import json
import logging
from pathlib import Path
from typing import Optional, Set, Tuple, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.db.models.satellite_observation import SatelliteObservation

logger = logging.getLogger("jalnetra.satellite.image_resolver")

SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}


class ObservationImageResolver:
    """
    Authoritative visual image resolver for satellite observations.
    Safely resolves, verifies, and validates local visual image assets across
    multiple database fields, observation directory conventions, and path formats.
    """

    @classmethod
    def _is_valid_image_file(cls, path: Path) -> bool:
        """Verifies existence, regular file, supported extension, and non-zero size."""
        try:
            if not path.exists() or not path.is_file():
                return False
            if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                return False
            if path.stat().st_size <= 0:
                return False
            return True
        except (OSError, PermissionError):
            return False

    @classmethod
    def _is_safe_path(cls, path: Path, base_dir: Path) -> bool:
        """Prevents directory traversal escaping base_dir."""
        try:
            if ".." in path.parts:
                return False
            resolved = path.resolve()
            base_resolved = base_dir.resolve()
            return str(resolved).startswith(str(base_resolved))
        except Exception:
            return False

    @classmethod
    def resolve_visual_image(
        cls,
        observation: SatelliteObservation,
        data_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Resolves the actual local filesystem image file for a SatelliteObservation.
        Handles:
          - data/...
          - ./data/...
          - absolute filesystem paths
          - water-body-relative paths (e.g. water_bodies/{wb_id}/observations/{scene}/rgb.jpg)
          - observation-relative paths
          - metadata.json fallback
          - observation directory scan for supported images (.jpg, .jpeg, .png, .webp)
        Returns a validated Path if valid, else None.
        """
        if observation is None:
            return None

        effective_data_dir = data_dir or settings.resolved_data_dir
        wb_id = str(observation.water_body_id)
        scene_id = getattr(observation, "external_scene_id", None) or getattr(observation, "scene_id", None) or ""

        candidate_paths: List[Path] = []

        # 1. Primary candidate: observation.local_visual_path
        raw_path_str = getattr(observation, "local_visual_path", None)
        if raw_path_str:
            raw_path_str = raw_path_str.strip()
            # Normalize slashes
            p = Path(raw_path_str)

            # Check if absolute path
            if p.is_absolute():
                if cls._is_valid_image_file(p):
                    return p
            else:
                # Relative forms:
                # Strip leading "./data/" or "data/" if present when joining with data_dir
                parts = p.parts
                if len(parts) > 0 and parts[0] in ("data", ".data"):
                    cand = effective_data_dir / Path(*parts[1:])
                elif len(parts) > 1 and parts[0] == "." and parts[1] == "data":
                    cand = effective_data_dir / Path(*parts[2:])
                elif parts and parts[0] == "water_bodies":
                    cand = effective_data_dir / p
                elif parts and parts[0] == "observations":
                    cand = effective_data_dir / "water_bodies" / wb_id / p
                else:
                    cand = effective_data_dir / p

                if cls._is_safe_path(cand, effective_data_dir) and cls._is_valid_image_file(cand):
                    return cand
                candidate_paths.append(cand)

        # 2. Check metadata_json for alternative path references
        metadata_raw = getattr(observation, "metadata_json", None)
        if metadata_raw:
            try:
                meta = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                if isinstance(meta, dict):
                    for key in ("local_visual_path", "image_path", "visual_path", "rgb_path", "path"):
                        val = meta.get(key)
                        if val and isinstance(val, str):
                            p = Path(val.strip())
                            if p.is_absolute() and cls._is_valid_image_file(p):
                                return p
                            cand = effective_data_dir / p
                            if cls._is_safe_path(cand, effective_data_dir) and cls._is_valid_image_file(cand):
                                return cand
            except Exception as e:
                logger.debug("Error parsing metadata_json for observation %s: %s", observation.id, e)

        # 3. Convention-based search in observation directory
        # Standard: {data_dir}/water_bodies/{wb_id}/observations/{scene_id}/
        possible_dirs: List[Path] = []
        if scene_id:
            possible_dirs.append(effective_data_dir / "water_bodies" / wb_id / "observations" / scene_id)
        possible_dirs.append(effective_data_dir / "water_bodies" / wb_id / "observations" / str(observation.id))
        possible_dirs.append(effective_data_dir / "water_bodies" / wb_id / str(observation.id))

        standard_filenames = [
            "rgb.jpg", "rgb.jpeg", "rgb.png", "rgb.webp",
            "visual.jpg", "visual.jpeg", "visual.png",
            "image.jpg", "image.jpeg", "image.png",
        ]

        for d in possible_dirs:
            if not d.exists() or not d.is_dir():
                continue
            if not cls._is_safe_path(d, effective_data_dir):
                continue

            # Check standard filenames first
            for fname in standard_filenames:
                test_file = d / fname
                if cls._is_valid_image_file(test_file):
                    return test_file

            # Check any file with supported image extension in directory
            try:
                for entry in d.iterdir():
                    if cls._is_valid_image_file(entry):
                        return entry
            except (OSError, PermissionError):
                continue

        return None

    @classmethod
    def get_latest_visual_observation(
        cls,
        water_body_id: Any,
        db: Any,
        data_dir: Optional[Path] = None,
    ) -> Optional[Tuple[SatelliteObservation, Path]]:
        """
        Finds the newest observation for a water body that has a valid, verified local image.
        Sorts all observations by sensing_date descending, testing each until one with a valid
        image is found. Does NOT fail immediately on the newest observation.
        """
        # Defensive check for reversed parameters (db, water_body_id)
        if hasattr(water_body_id, "execute") and isinstance(db, str):
            water_body_id, db = db, water_body_id
        stmt = (
            select(SatelliteObservation)
            .where(SatelliteObservation.water_body_id == water_body_id)
            .order_by(SatelliteObservation.sensing_date.desc())
        )
        observations = db.execute(stmt).scalars().all()

        for obs in observations:
            resolved_path = cls.resolve_visual_image(obs, data_dir=data_dir)
            if resolved_path is not None:
                return (obs, resolved_path)

        return None
