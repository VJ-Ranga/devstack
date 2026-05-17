import os
import sys
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <!-- Dynamic modern circular container -->
  <rect width="512" height="512" rx="128" fill="#F5F3F0" stroke="#E5E2DC" stroke-width="12"/>
  
  <!-- Dynamic stack elements in center -->
  <g transform="translate(128, 128)">
    <!-- Bottom layer: MariaDB (charcoal) -->
    <rect x="0" y="180" width="256" height="44" rx="22" fill="#5E5B56"/>
    <!-- Middle layer: PHP (ochre) -->
    <rect x="32" y="90" width="192" height="44" rx="22" fill="#BF8E3B"/>
    <!-- Top layer: Nginx/Apache (terracotta) -->
    <rect x="64" y="0" width="128" height="44" rx="22" fill="#E55B3C"/>
  </g>
  
  <!-- Status dot on top right -->
  <circle cx="410" cy="102" r="22" fill="#E55B3C"/>
</svg>"""

def main():
    # We must have an active QApplication context to render SVGs
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Setup renderer
    renderer = QSvgRenderer(SVG_CONTENT.encode("utf-8"))
    if not renderer.isValid():
        print("Error: Invalid SVG content")
        return
        
    # Render sizes
    sizes = [16, 32, 48, 64, 128, 256]
    pixmaps = []
    
    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        from PySide6.QtGui import QPainter
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmaps.append(pixmap)
        
    # Paths
    app_dir = os.path.dirname(os.path.abspath(__file__))
    template_htdocs = os.path.abspath(os.path.join(app_dir, "..", "devstack-template", "htdocs"))
    
    # Save standard PNG files
    png_path = os.path.join(app_dir, "assets", "icon.png")
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    pixmaps[-1].save(png_path, "PNG")
    print(f"Saved PNG to {png_path}")
    
    # Save standard ICO files
    ico_path = os.path.join(app_dir, "assets", "icon.ico")
    pixmaps[-1].save(ico_path, "ICO")
    print(f"Saved ICO to {ico_path}")
    
    # Save to local htdocs favicon if folder exists
    if os.path.isdir(template_htdocs):
        fav_png = os.path.join(template_htdocs, "favicon.png")
        fav_ico = os.path.join(template_htdocs, "favicon.ico")
        pixmaps[-1].save(fav_png, "PNG")
        pixmaps[-1].save(fav_ico, "ICO")
        print(f"Saved favicons to {template_htdocs}")
    else:
        print("Warning: devstack-template/htdocs directory not found, skipping favicons.")

if __name__ == "__main__":
    main()
