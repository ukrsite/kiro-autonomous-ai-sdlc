from pptx import Presentation
import os
from pathlib import Path
import base64

def get_image_description(image_path):
    """Generate a text description of an image."""
    return f"[Image at {image_path} - description to be added by vision analysis]"

def extract_ppt_to_markdown(pptx_path, describe_images=True):
    """Extract PowerPoint content to markdown with images and optional descriptions."""
    
    pptx_path = Path(pptx_path)
    output_dir = pptx_path.parent
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    prs = Presentation(str(pptx_path))
    markdown_content = []
    
    base_name = pptx_path.stem
    markdown_content.append(f"# {base_name}\n\n")
    
    image_counter = 0
    
    for slide_num, slide in enumerate(prs.slides, 1):
        markdown_content.append(f"## Slide {slide_num}\n\n")
        
        for shape in slide.shapes:
            if shape.has_table:
                table = shape.table
                markdown_content.append("\n")
                for row_idx, row in enumerate(table.rows):
                    row_data = []
                    for cell in row.cells:
                        cell_text = cell.text.strip().replace("\n", " ")
                        row_data.append(cell_text)
                    markdown_content.append("| " + " | ".join(row_data) + " |\n")
                    if row_idx == 0:
                        markdown_content.append("| " + " | ".join(["---"] * len(row_data)) + " |\n")
                markdown_content.append("\n")
            
            elif shape.shape_type == 13:
                try:
                    image = shape.image
                    image_counter += 1
                    image_filename = f"slide_{slide_num}_img_{image_counter}.{image.ext}"
                    image_path = images_dir / image_filename
                    with open(image_path, 'wb') as f:
                        f.write(image.blob)
                    markdown_content.append(f"\n![Image](images/{image_filename})\n\n")
                    if describe_images:
                        print(f"  Analyzing image {image_counter}...")
                        description = get_image_description(image_path)
                        markdown_content.append(f"**Image Description:** {description}\n\n")
                except Exception as e:
                    print(f"Could not extract image from slide {slide_num}: {e}")
            
            elif shape.shape_type == 14:
                try:
                    if hasattr(shape, 'image'):
                        image = shape.image
                        image_counter += 1
                        image_filename = f"slide_{slide_num}_img_{image_counter}.{image.ext}"
                        image_path = images_dir / image_filename
                        with open(image_path, 'wb') as f:
                            f.write(image.blob)
                        markdown_content.append(f"\n![Image](images/{image_filename})\n\n")
                        if describe_images:
                            print(f"  Analyzing image {image_counter}...")
                            description = get_image_description(image_path)
                            markdown_content.append(f"**Image Description:** {description}\n\n")
                except Exception:
                    pass
            
            if hasattr(shape, "text") and shape.text.strip():
                text = shape.text.strip()
                if shape == slide.shapes[0] and slide_num > 1:
                    markdown_content.append(f"### {text}\n\n")
                else:
                    if hasattr(shape, "text_frame"):
                        for paragraph in shape.text_frame.paragraphs:
                            level = paragraph.level
                            text = paragraph.text.strip()
                            if text:
                                indent = "  " * level
                                markdown_content.append(f"{indent}- {text}\n")
                    else:
                        markdown_content.append(f"{text}\n\n")
        
        markdown_content.append("\n---\n\n")
    
    md_path = output_dir / f"{base_name}.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("".join(markdown_content))
    
    return md_path, image_counter

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python convert_ppt.py <path_to_pptx_file> [--no-describe]")
        sys.exit(1)
    
    pptx_file = sys.argv[1]
    describe_images = "--no-describe" not in sys.argv
    
    if not os.path.exists(pptx_file):
        print(f"Error: File not found: {pptx_file}")
        sys.exit(1)
    
    print(f"Converting: {pptx_file}")
    if describe_images:
        print("Image descriptions will be generated using AI vision...")
    
    md_file, img_count = extract_ppt_to_markdown(pptx_file, describe_images)
    print(f"\n✓ Conversion complete!")
    print(f"  Markdown file: {md_file}")
    print(f"  Images extracted: {img_count}")
