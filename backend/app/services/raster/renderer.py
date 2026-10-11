"""
RGB Raster Alignment and Visualization Renderer.
Reprojects Sentinel-2 B04 (Red), B03 (Green), and B02 (Blue) GeoTIFFs to EPSG:4326,
aligns grids, handles NoData/invalid pixels, performs percentile contrast stretching,
and renders an RGBA PNG for Leaflet ImageOverlay.
"""
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from app.services.raster.models import GeoBounds


class RGBRenderer:
    """Renders aligned, reprojected, contrast-stretched RGB visualizations from Sentinel-2 bands."""

    @staticmethod
    def render_rgb(
        red_path: Path,
        green_path: Path,
        blue_path: Path,
        output_png_path: Path,
        max_dimension: int = 1024,
        lower_percentile: float = 2.0,
        upper_percentile: float = 98.0,
    ) -> Dict[str, Any]:
        """
        Takes red (B04), green (B03), and blue (B02) GeoTIFFs,
        reprojects them on the fly to EPSG:4326 using WarpedVRT,
        resamples them to a common grid capped at max_dimension,
        applies percentile-based contrast stretch to valid pixels,
        masks nodata/zero pixels transparently, and saves an RGBA PNG.

        Returns geographic bounds (EPSG:4326) and dimensions.
        """
        for p in (red_path, green_path, blue_path):
            if not p.exists():
                raise FileNotFoundError(f"Band file not found: {p}")

        # Open bands
        with rasterio.open(red_path) as src_r, \
             rasterio.open(green_path) as src_g, \
             rasterio.open(blue_path) as src_b:

            # Use WarpedVRT to reproject all 3 bands to EPSG:4326 on the fly
            vrt_kwargs = {"crs": "EPSG:4326", "resampling": Resampling.bilinear}
            with WarpedVRT(src_r, **vrt_kwargs) as vrt_r, \
                 WarpedVRT(src_g, **vrt_kwargs) as vrt_g, \
                 WarpedVRT(src_b, **vrt_kwargs) as vrt_b:

                bounds = vrt_r.bounds
                geo_bounds = GeoBounds(
                    west=float(bounds.left),
                    south=float(bounds.bottom),
                    east=float(bounds.right),
                    north=float(bounds.top),
                )

                # Determine output grid dimensions respecting aspect ratio
                aspect = vrt_r.width / max(1, vrt_r.height)
                if aspect >= 1.0:
                    out_w = max_dimension
                    out_h = max(1, int(max_dimension / aspect))
                else:
                    out_w = max(1, int(max_dimension * aspect))
                    out_h = max_dimension

                # Read downsampled 2D arrays from each warped band
                r_arr = vrt_r.read(1, out_shape=(out_h, out_w), resampling=Resampling.bilinear)
                g_arr = vrt_g.read(1, out_shape=(out_h, out_w), resampling=Resampling.bilinear)
                b_arr = vrt_b.read(1, out_shape=(out_h, out_w), resampling=Resampling.bilinear)

                # Identify valid pixels: finite, not nodata, and positive
                # In Sentinel-2 L2A surface reflectance, 0 is typically nodata / off-swath
                valid_mask = (
                    np.isfinite(r_arr) & (r_arr > 0) &
                    np.isfinite(g_arr) & (g_arr > 0) &
                    np.isfinite(b_arr) & (b_arr > 0)
                )

                # Apply nodata checks if defined on sources
                for src, arr in ((src_r, r_arr), (src_g, g_arr), (src_b, b_arr)):
                    if src.nodata is not None:
                        valid_mask &= (arr != src.nodata)

                # Apply contrast stretch on valid pixels
                stretched_channels = []
                for channel_arr in (r_arr, g_arr, b_arr):
                    valid_vals = channel_arr[valid_mask]
                    if len(valid_vals) > 0:
                        p_low = float(np.percentile(valid_vals, lower_percentile))
                        p_high = float(np.percentile(valid_vals, upper_percentile))
                        if p_high > p_low:
                            scaled = np.clip((channel_arr - p_low) / (p_high - p_low) * 255.0, 0, 255)
                            stretched = scaled.astype(np.uint8)
                        else:
                            stretched = np.zeros_like(channel_arr, dtype=np.uint8)
                    else:
                        stretched = np.zeros_like(channel_arr, dtype=np.uint8)
                    stretched_channels.append(stretched)

                # Set alpha channel: 255 for valid data, 0 for off-swath/nodata
                alpha = np.where(valid_mask, 255, 0).astype(np.uint8)

                # Stack RGBA (Red=B04, Green=B03, Blue=B02, Alpha)
                rgba = np.stack(
                    [stretched_channels[0], stretched_channels[1], stretched_channels[2], alpha],
                    axis=-1,
                )

                # Ensure output directory exists
                output_png_path.parent.mkdir(parents=True, exist_ok=True)

                # Save optimized RGBA PNG
                img = Image.fromarray(rgba)
                img.save(output_png_path, format="PNG", optimize=True)

                return {
                    "output_path": output_png_path,
                    "width": out_w,
                    "height": out_h,
                    "bounds": geo_bounds,
                    "crs": "EPSG:4326",
                }
