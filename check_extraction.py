"""Check what data is being extracted from uploaded files."""
import sys, os
sys.path.insert(0, '.')

from document_processing.document_processor import DocumentProcessor
from document_processing.extractor import InformationExtractor
from models.document import Document
from utils.enums import DocumentType

dp = DocumentProcessor()
uploads_dir = 'data/uploads'

for app_dir in sorted(os.listdir(uploads_dir)):
    app_path = os.path.join(uploads_dir, app_dir)
    if not os.path.isdir(app_path):
        continue
    print(f'=== Application {app_dir} ===')
    for fname in sorted(os.listdir(app_path)):
        fpath = os.path.join(app_path, fname)
        size = os.path.getsize(fpath)

        fl = fname.lower()
        if 'salary' in fl or 'pay' in fl or 'slip' in fl:
            dtype = 'salary_slip'
        elif 'bank' in fl or 'statement' in fl:
            dtype = 'bank_statement'
        elif 'employ' in fl or 'offer' in fl or 'letter' in fl:
            dtype = 'employment_letter'
        else:
            dtype = 'other'

        result = dp.process(fpath, dtype)
        vs = result['validation_status'].value
        method = result['extraction_method']

        ed = result['metadata'].get('extracted_data', {})
        text_preview = result['extracted_text'][:80].replace('\n', '\\n')

        print(f'  {fname} ({size}B)')
        print(f'    method={method}, status={vs}')
        print(f'    text: "{text_preview}"')
        if ed:
            print(f'    extracted:')
            for k, v in ed.items():
                if k in ('source_documents', 'field_sources', 'validation_warnings', 'metadata', 'confidence_score', 'ocr_confidence') or v is None:
                    continue
                if isinstance(v, dict) and not v:
                    continue
                print(f'      {k}: {v}')
        else:
            missing = result['metadata'].get('missing_fields', [])
            if missing:
                print(f'    missing_fields: {missing}')
        print()

print('=== Done ===')
