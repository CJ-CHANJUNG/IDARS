"""
PDF Splitter API Wrapper
Adapts the existing pdf_splitter.py to work with dynamic project paths
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

# Add the Modules/Splitter directory to path
# __file__ is backend/logic/pdf_splitter_api.py
# parent -> backend/logic
# parent.parent -> backend
# parent.parent.parent -> IDARS PJT (Root)
SPLITTER_DIR = Path(__file__).parent.parent.parent / 'Modules' / 'Splitter'
sys.path.insert(0, str(SPLITTER_DIR))

from pdf_splitter import PDFSplitter as OriginalPDFSplitter, DOCUMENT_PATTERNS, DOCUMENT_ID_PATTERNS
import fitz


class ProjectPDFSplitter:
    """
    Wrapper around PDFSplitter that works with project-specific directories
    """
    
    def __init__(self, project_id: str, projects_dir: str = "Data/projects"):
        self.project_id = project_id
        self.project_path = Path(projects_dir) / project_id
        self.input_dir = self.project_path / "step2_evidence_collection" / "DMS_Downloads"
        self.output_dir = self.project_path / "step2_evidence_collection" / "split_documents"
        self.thumbnails_dir = self.project_path / "step2_evidence_collection" / "thumbnails"
        
    def split_all_pdfs(self, target_documents: Optional[List[str]] = None, progress_callback=None) -> Dict:
        """
        Split PDFs in DMS_Downloads folder and organize by billing document
        Args:
            target_documents: Optional list of billing document numbers to process. If None, process all.
            progress_callback: Optional callback function(current, total, doc_number, message)
        Returns summary of split operation
        """
        if not self.input_dir.exists():
            return {"error": "DMS_Downloads folder not found", "files_processed": 0}
        
        # Recursive search for PDFs to handle subdirectories like 'Billing'
        pdf_files = list(self.input_dir.rglob("*.pdf"))
        if not pdf_files:
            return {"error": "No PDF files found in DMS_Downloads", "files_processed": 0}
        
        # Filter by target_documents if provided
        if target_documents:
            targets = [str(t) for t in target_documents]
            filtered_files = []
            for f in pdf_files:
                for t in targets:
                    if f.name.startswith(t):
                        filtered_files.append(f)
                        break
            pdf_files = filtered_files
            
            if not pdf_files:
                return {"error": "No matching PDF files found for selected documents", "files_processed": 0}

        # Group PDFs by billing document number for better organization
        from collections import defaultdict
        billing_groups = defaultdict(list)
        for pdf_file in pdf_files:
            billing_doc = pdf_file.stem.split('_')[0]
            billing_groups[billing_doc].append(pdf_file)
        
        print(f"[SPLITTER] Found {len(billing_groups)} billing documents with {len(pdf_files)} total PDF files")
        for billing_doc, files in billing_groups.items():
            print(f"  {billing_doc}: {len(files)} file(s)")

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        total_splits = 0
        processed_billing_docs = set()  # Track which billing docs we've already cleaned up
        
        # Get total billing documents for progress
        total_billing_docs = len(billing_groups)
        current_doc_index = 0
        
        # Process files in order, but grouped by billing document
        for billing_doc, pdf_file_list in billing_groups.items():
            doc_output_dir = self.output_dir / billing_doc
            
            # CLEANUP: Remove existing folder ONCE per billing document (before first file)
            if billing_doc not in processed_billing_docs:
                if doc_output_dir.exists():
                    import shutil
                    shutil.rmtree(doc_output_dir)
                    print(f"[CLEANUP] Removed existing split folder for {billing_doc}")
                processed_billing_docs.add(billing_doc)
            
            # Create output folder
            doc_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process each PDF file individually
            for pdf_file in sorted(pdf_file_list, key=lambda x: x.name):
                try:
                    print(f"[SPLIT] Processing {pdf_file.name}")
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(current_doc_index, total_billing_docs, billing_doc, f"Processing {pdf_file.name}")
                    
                    # Extract identifier from original filename (remove billing doc number and extension)
                    # Example: "94459198_CONTI AS.pdf" -> "CONTI AS"
                    original_stem = pdf_file.stem  # filename without extension
                    if '_' in original_stem:
                        # Remove billing doc number prefix
                        file_identifier = '_'.join(original_stem.split('_')[1:])  
                    else:
                        file_identifier = original_stem
                    
                    # Sanitize identifier for filename (remove special chars, limit length)
                    import re
                    file_identifier = re.sub(r'[^\w\s-]', '', file_identifier)  # Keep alphanumeric, spaces, hyphens
                    file_identifier = file_identifier.replace(' ', '_')[:30]  # Replace spaces, limit to 30 chars
                    
                    # Use adapted splitter - each PDF is split independently
                    with AdaptedPDFSplitter(str(pdf_file), str(doc_output_dir), billing_doc, file_identifier) as splitter:
                        split_results = splitter.process()
                        
                        results.append({
                            "billing_document": billing_doc,
                            "original_file": pdf_file.name,
                            "splits": split_results,
                            "split_count": len(split_results)
                        })
                        total_splits += len(split_results)
                        
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    results.append({
                        "billing_document": billing_doc,
                        "original_file": pdf_file.name,
                        "error": str(e)
                    })
            
            # Increment after processing all files for this billing doc
            current_doc_index += 1
            if progress_callback:
                progress_callback(current_doc_index, total_billing_docs, billing_doc, f"Completed {billing_doc}")
        
        # Save results metadata (Merge with existing if partial update?)
        # For now, just save what we did. The frontend relies on file existence mostly.
        # If we want to maintain a master list, we should load existing metadata.
        metadata_path = self.output_dir / "split_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                "split_date": datetime.now().isoformat(),
                "files_processed": len(pdf_files),
                "total_splits": total_splits,
                "results": results
            }, f, indent=2, ensure_ascii=False)
        
        return {
            "files_processed": len(pdf_files),
            "total_splits": total_splits,
            "results": results
        }


class AdaptedPDFSplitter(OriginalPDFSplitter):
    """
    Modified version of PDFSplitter that doesn't copy to Parser folders
    """
    def __init__(self, input_path: str, output_dir: str, billing_doc: str, file_identifier: str = ""):
        self.pdf_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.doc = None
        self.slip_no = billing_doc  # Use billing doc as slip_no
        self.file_identifier = file_identifier  # Identifier from original filename
        
    def __enter__(self):
        self.doc = fitz.open(str(self.pdf_path))
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()
            
    def process(self):
        """
        Modified process that saves files in organized subfolder structure:
        - extraction_targets/: BL and Invoice (for Step 3 extraction)
        - others/: All other document types
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        groups = self.group_pages()
        saved_files = []
        
        # Define extraction target types
        EXTRACTION_TARGETS = ['Bill_of_Lading', 'Commercial_Invoice']
        
        for grp in groups:
            doc_type = grp['type']
            pages = grp['pages']
            start, end = pages[0]+1, pages[-1]+1
            
            out_pdf = fitz.open()
            out_pdf.insert_pdf(self.doc, from_page=pages[0], to_page=pages[-1])
            
            page_str = f"{start}p" if start == end else f"{start}-{end}p"
            
            # Build filename with original file identifier to avoid conflicts
            # Format: {billing_doc}_{doc_type}_{file_identifier}_{page_str}.pdf
            if self.file_identifier:
                filename = f"{self.slip_no}_{doc_type}_{self.file_identifier}_{page_str}.pdf"
            else:
                filename = f"{self.slip_no}_{doc_type}_{page_str}.pdf"
            
            # Determine subfolder based on document type
            if doc_type in EXTRACTION_TARGETS:
                subfolder = 'extraction_targets'
            else:
                subfolder = 'others'
            
            # Create subfolder and save file
            subfolder_path = self.output_dir / subfolder
            subfolder_path.mkdir(parents=True, exist_ok=True)
            
            save_path = subfolder_path / filename
            out_pdf.save(str(save_path))
            out_pdf.close()
            
            saved_files.append({
                "file_name": filename, 
                "slip_no": self.slip_no, 
                "document_type": doc_type,
                "subfolder": subfolder,  # Track which subfolder it went to
                "page_range": [start, end], 
                "document_id": grp['id'], 
                "classification_log": grp['log']
            })
            print(f" ✅ Saved: {subfolder}/{filename}")
            
        return saved_files


def split_evidence_pdfs(project_id: str, projects_dir: str = "Data/projects", target_documents: Optional[List[str]] = None, progress_callback=None) -> Dict:
    """
    Main entry point for splitting PDFs for a project
    Args:
        project_id: Project identifier
        projects_dir: Base projects directory path
        target_documents: Optional list of billing document numbers to process
        progress_callback: Optional callback function(current, total, doc_number, message)
    Returns summary with file counts and results
    """
    splitter = ProjectPDFSplitter(project_id, projects_dir)
    return splitter.split_all_pdfs(target_documents, progress_callback)
