"""Docling SDK adapter, run only by the project's isolated Python environment."""
import importlib.metadata
from contextlib import redirect_stdout
import json
from pathlib import Path
import platform
import sys


def versions():
    packages = {p.metadata['Name']: p.version for p in importlib.metadata.distributions()}
    return dict(docling=packages.get('docling'), python=platform.python_version(), packages=packages)


def prepare(models):
    from docling.utils.model_downloader import download_models
    download_models(output_dir=models, with_layout=True, with_tableformer=True,
                    with_code_formula=False, with_picture_classifier=False,
                    with_rapidocr=True, rapidocr_models=['onnxruntime:latin'], progress=False)


def convert(request):
    from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    from docling.datamodel.backend_options import HTMLBackendOptions, MsWordBackendOptions
    from docling.datamodel.base_models import ConversionStatus, InputFormat
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
    options = PdfPipelineOptions(artifacts_path=models, document_timeout=1800,
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
    result = converter.convert(source, raises_on_error=False, max_num_pages=500, max_file_size=100 * 1024 * 1024)
    state = {ConversionStatus.SUCCESS: 'ready', ConversionStatus.PARTIAL_SUCCESS: 'partial'}.get(result.status, 'failed')
    warnings = [] if state == 'ready' else ['incomplete_conversion']
    coverage = {'pages': sorted(result.document.pages)} if result.document else {}
    if state in ('ready', 'partial'):
        text = result.document.export_to_markdown()
        if not text.strip():
            state = 'partial'
            warnings.append('empty_extraction')
        result.document.save_as_markdown(output / 'content.md', artifacts_dir=output / 'assets',
                                         image_mode=ImageRefMode.REFERENCED)
        result.document.save_as_json(output / 'document.json', image_mode=ImageRefMode.EMBEDDED)
    return dict(state=state, warnings=warnings, coverage=coverage,
                converter=dict(package='docling', version=importlib.metadata.version('docling'), profile='documents',
                               models=['layout', 'tableformer', 'rapidocr-onnxruntime-latin'],
                               options=dict(max_pages=500, max_bytes=100 * 1024 * 1024, timeout=1800,
                                            remote_fetch=False, local_fetch=False, device='cpu')))


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'versions':
            result = versions()
        elif sys.argv[1] == 'prepare':
            with redirect_stdout(sys.stderr):
                prepare(Path(sys.argv[2]))
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
