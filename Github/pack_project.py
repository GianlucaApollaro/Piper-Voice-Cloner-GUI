import os
import zipfile

def pack_project():
    output_filename = "Piper_Voice_Cloner_GUI_v1.0.zip"
    print(f"Packaging project into {output_filename}...")
    
    # Directories/Files to completely ignore
    ignore_dirs = {
        '.git', 'venv', '.venv', '__pycache__', 
        'dataset', 'processed', 'Datasets', 
        'lightning_logs', 'exported_model', 
        'models_cache', 'checkpoints', '.vscode', '.idea',
        'Github'
    }
    ignore_files = {
        output_filename,
        'Piper_Voice_Cloner_GUI_v1.0.zip'
    }
    
    # We run relative to the parent directory of Github, i.e., project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    zip_path = os.path.join(project_root, output_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_root):
            # Calculate relative path components
            rel_path = os.path.relpath(root, project_root)
            path_parts = rel_path.split(os.sep)
            
            # Skip if any parent folder is ignored
            if any(part in ignore_dirs for part in path_parts):
                continue
                
            # Filter out ignored directories in-place to prevent os.walk from entering them
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                if file in ignore_files or file.endswith('.zip') or file.endswith('.7z'):
                    continue
                file_path = os.path.join(root, file)
                archive_name = os.path.relpath(file_path, project_root)
                zipf.write(file_path, archive_name)
                print(f"Added: {archive_name}")
                
    print(f"\nSuccessfully packed project into: {zip_path}")

if __name__ == "__main__":
    pack_project()
