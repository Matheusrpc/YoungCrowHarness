"""Docling SDK adapter, run only by the project's isolated Python environment."""
import importlib.metadata
from contextlib import redirect_stdout
from io import BytesIO
import json
from pathlib import Path
import platform
import subprocess
import sys


def versions():
    packages = {p.metadata['Name']: p.version for p in importlib.metadata.distributions()}
    return dict(docling=packages.get('docling'), python=platform.python_version(), packages=packages)


def prepare(models, profile='documents'):
    if profile == 'media':
        import whisper
        whisper.load_model('base', device='cpu', download_root=str(models))
        return
    from docling.utils.model_downloader import download_models
    download_models(output_dir=models, with_layout=True, with_tableformer=True,
                    with_code_formula=False, with_picture_classifier=False,
                    with_rapidocr=True, rapidocr_models=['onnxruntime:latin'], progress=False)


def media_result(status, document, media):
    state = {'success': 'ready', 'partial_success': 'partial'}.get(status, 'failed')
    warnings = [] if state == 'ready' else ['incomplete_conversion']
    intervals, frames = [], []
    for item in document.get('texts', []):
        for source in item.get('source', []):
            if item.get('text', '').strip() and 'start_time' in source and 'end_time' in source:
                intervals.append([source['start_time'], source['end_time']])
    for item in document.get('pictures', []):
        for source in item.get('source', []):
            if 'start_time' in source:
                frames.append(source['start_time'])
    for condition, warning in ((not media['has_audio'], 'audio_track_absent'),
                               (media['has_audio'] and not intervals, 'transcript_empty'),
                               (media['has_video'] and not frames, 'video_frames_absent'),
                               (len(frames) >= 200 and media['duration_seconds'] > 2000, 'frame_limit_reached')):
        if condition:
            warnings.append(warning)
            if state == 'ready':
                state = 'partial'
    coverage = dict(duration_seconds=media['duration_seconds'], transcript_intervals=intervals,
                    frame_times=frames, sampled_frames=len(frames))
    return state, coverage, warnings


def convert(request, *, document_timeout=1800):
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    from docling.datamodel.backend_options import HTMLBackendOptions, MsWordBackendOptions
    from docling.datamodel.base_models import ConversionStatus, DocumentStream, InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import (DocumentConverter, HTMLFormatOption, WordFormatOption,
                                            PdfFormatOption, ImageFormatOption)
    from docling_core.types.doc import ImageRefMode

    # A second guard besides the backend flags and offline model cache. This is
    # process-local Python network denial, not an OS sandbox for hostile binaries.
    def deny_network(event, args):
        if event == 'socket.connect':
            raise PermissionError('Network disabled during conversion.')
    sys.addaudithook(deny_network)
    source, output, models = (Path(request[key]) for key in ('source', 'output', 'models'))
    profile = request.get('profile', 'documents')
    media = request.get('media')
    if profile == 'media':
        from docling.datamodel import asr_model_specs
        from docling.datamodel.pipeline_options import AsrPipelineOptions, VideoPipelineOptions
        from docling.document_converter import AudioFormatOption, VideoFormatOption
        from docling.pipeline.asr_pipeline import AsrPipeline
        settings = dict(artifacts_path=models, document_timeout=document_timeout,
                        accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU),
                        asr_options=asr_model_specs.WHISPER_BASE_NATIVE)
        if not media['has_video']:
            # Whisper's own decoder autodetects inputs. Give it a local PCM WAV
            # produced with an explicit demuxer and file-only protocol instead.
            from documents import MEDIA_FORMATS
            normalized = output / 'normalized.wav'
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file',
                            '-f', MEDIA_FORMATS[source.suffix.lower()], '-i', 'file:' + str(source.absolute()),
                            '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(normalized)],
                           check=True, capture_output=True, timeout=1800)
            source = normalized
        converter = DocumentConverter(allowed_formats=[InputFormat.AUDIO, InputFormat.VIDEO], format_options={
            InputFormat.AUDIO: AudioFormatOption(pipeline_cls=AsrPipeline, pipeline_options=AsrPipelineOptions(**settings)),
            InputFormat.VIDEO: VideoFormatOption(pipeline_options=VideoPipelineOptions(**settings,
                max_sampled_frames=200, enable_diarization=False))})
    else:
        options = PdfPipelineOptions(artifacts_path=models, document_timeout=document_timeout,
                                 generate_picture_images=True,
                                 accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU),
                                 ocr_options=RapidOcrOptions(backend='onnxruntime', lang=['latin']))
        converter = DocumentConverter(allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.IMAGE, InputFormat.HTML],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options),
                        InputFormat.IMAGE: ImageFormatOption(pipeline_options=options),
                        InputFormat.HTML: HTMLFormatOption(backend_options=HTMLBackendOptions(
                            fetch_images=False, render_page=False, enable_remote_fetch=False, enable_local_fetch=False)),
                        InputFormat.DOCX: WordFormatOption(backend_options=MsWordBackendOptions(
                            enable_remote_fetch=False, enable_local_fetch=False))})
    if profile == 'documents' and source.suffix.lower() in ('.html', '.htm'):
        # These are preserved bytes, not a local website. A Path makes Docling
        # resolve page hyperlinks against our storage directory. A stream keeps
        # them as references; the vault neutralizes non-HTTP(S) destinations.
        with source.open('rb') as html:
            content = html.read(100 * 1024 * 1024 + 1)
        if len(content) > 100 * 1024 * 1024:
            raise ValueError('HTML source exceeds size limit.')
        source = DocumentStream(name=source.name, stream=BytesIO(content))
    result = converter.convert(source, raises_on_error=False, max_num_pages=500,
                               max_file_size=(500 if profile == 'media' else 100) * 1024 * 1024)
    state = {ConversionStatus.SUCCESS: 'ready', ConversionStatus.PARTIAL_SUCCESS: 'partial'}.get(result.status, 'failed')
    warnings = [] if state == 'ready' else ['incomplete_conversion']
    coverage = {'pages': sorted(result.document.pages)} if result.document else {}
    if profile == 'media':
        state, coverage, warnings = media_result(result.status.value, result.document.export_to_dict() if result.document else {}, media)
    if state in ('ready', 'partial'):
        text = result.document.export_to_markdown()
        if not text.strip():
            state = 'partial'
            warnings.append('empty_extraction')
        result.document.save_as_markdown(output / 'content.md', artifacts_dir=output / 'assets',
                                         image_mode=ImageRefMode.REFERENCED)
        result.document.save_as_json(output / 'document.json', image_mode=ImageRefMode.EMBEDDED)
    if profile == 'media':
        (output / 'normalized.wav').unlink(missing_ok=True)
    return dict(state=state, warnings=warnings, coverage=coverage,
                converter=dict(package='docling', version=importlib.metadata.version('docling'), profile=profile,
                               models=['whisper-base-native'] if profile == 'media' else ['layout', 'tableformer', 'rapidocr-onnxruntime-latin'],
                               options=dict(max_pages=500, max_bytes=(500 if profile == 'media' else 100) * 1024 * 1024, timeout=document_timeout,
                                            remote_fetch=False, local_fetch=False, device='cpu')))


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'versions':
            result = versions()
        elif sys.argv[1] == 'prepare':
            with redirect_stdout(sys.stderr):
                prepare(Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else 'documents')
            result = {'state': 'ready'}
        else:
            with redirect_stdout(sys.stderr):
                result = convert(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
        print(json.dumps(result))
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stderr)  # Parent keeps diagnostics in private storage only.
        # Exceptions can embed private source text and paths. The protocol must not.
        print(json.dumps({'state': 'failed', 'warnings': ['worker_failed'], 'coverage': {}}))
        raise SystemExit(1)
