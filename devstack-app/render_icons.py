import io
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
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
    <!-- Top layer: Nginx (terracotta) -->
    <rect x="64" y="0" width="128" height="44" rx="22" fill="#E55B3C"/>
  </g>

  <!-- Status dot on top right -->
  <circle cx="410" cy="102" r="22" fill="#E55B3C"/>
</svg>"""


def _render_at(renderer: QSvgRenderer, size: int) -> QPixmap:
    """Render the SVG into a square QPixmap at the given pixel size."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def _save_ico(pixmaps: list[QPixmap], path: str) -> None:
    """
    Save a multi-size ICO file.
    Uses Pillow for proper multi-resolution embedding when available;
    falls back to saving the largest frame only (acceptable on modern Windows).
    """
    try:
        from PIL import Image
        from PySide6.QtCore import QBuffer, QByteArray

        pil_images = []
        for pm in pixmaps:
            ba = QByteArray()
            buf = QBuffer(ba)
            buf.open(QBuffer.WriteOnly)
            pm.save(buf, "PNG")
            buf.close()
            pil_images.append(Image.open(io.BytesIO(bytes(ba))).copy())

        pil_images[0].save(
            path,
            format="ICO",
            sizes=[(img.width, img.height) for img in pil_images],
            append_images=pil_images[1:],
        )
    except ImportError:
        # Pillow not installed — save largest frame only
        pixmaps[-1].save(path, "ICO")


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    renderer = QSvgRenderer(SVG_CONTENT.encode("utf-8"))
    if not renderer.isValid():
        print("Error: Invalid SVG content")
        return

    app_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(app_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    template_htdocs = os.path.abspath(
        os.path.join(app_dir, "..", "devstack-template", "htdocs")
    )

    # Render each size once
    ico_sizes   = [16, 32, 48, 256]
    ico_pixmaps = [_render_at(renderer, s) for s in ico_sizes]
    pm256 = ico_pixmaps[-1]  # largest for PNG export

    # App assets (desktop icon)
    png_path = os.path.join(assets_dir, "icon.png")
    pm256.save(png_path, "PNG")
    print(f"Saved PNG: {png_path}")

    ico_path = os.path.join(assets_dir, "icon.ico")
    _save_ico(ico_pixmaps, ico_path)
    print(f"Saved ICO: {ico_path}")

    # Dashboard favicon ONLY — not the htdocs root.
    #
    # Placing favicon.ico in htdocs/ root means every WordPress/PHP/Laravel site
    # shows the DevStack software icon in its browser tab instead of its own
    # favicon. Only the dashboard subfolder gets the icon so the dashboard tab
    # looks right and all other sites are completely unaffected.
    dashboard_dir = os.path.join(template_htdocs, "dashboard")
    if os.path.isdir(dashboard_dir):
        pm256.save(os.path.join(dashboard_dir, "favicon.png"), "PNG")
        _save_ico(ico_pixmaps[:3], os.path.join(dashboard_dir, "favicon.ico"))
        print(f"Saved dashboard favicons: {dashboard_dir}")
    elif os.path.isdir(template_htdocs):
        print("Warning: htdocs/dashboard not found — skipping favicons.")
    else:
        print("Warning: devstack-template/htdocs not found — skipping favicons.")


if __name__ == "__main__":
    main()
