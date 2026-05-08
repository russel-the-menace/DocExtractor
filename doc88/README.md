# Doc88 Extractor

## Technical Notes

- Extracts config from page `m_main.init(...)` and decodes `pageInfo`.
- Uses a custom base64 table to rebuild page IDs.
- Downloads PH/PK EBT chunks, zlib-decompresses, then reassembles SWF.
- Converts SWF to PDF (or SVG -> PDF) using ffdec.
- Merges pages with pypdf and outputs a single PDF.

## Data Flow

1) Parse page config -> page IDs
2) Download PH/PK chunks -> build SWF
3) Convert SWF -> PDF (or SVG -> PDF)
4) Merge -> output
