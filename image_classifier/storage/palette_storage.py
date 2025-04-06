import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List
from image_classifier.color import Color, ColorType

@dataclass
class Palette:
    """Data structure for storing a color palette"""
    name: str
    colors: List[Color]
    date_created: str

    def to_dict(self) -> dict:
        """Convert the palette to a dictionary for JSON storage"""
        return {
            "name": self.name,
            "colors": [color.rgb for color in self.colors],
            "date_created": self.date_created
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Palette':
        """Create a Palette instance from a dictionary"""
        return cls(
            name=data["name"],
            colors=[Color(rgb, ColorType.RGB) for rgb in data["colors"]],
            date_created=data["date_created"]
        )

class PaletteStorage:
    """Handles saving and loading palettes"""
    
    def __init__(self, storage_dir: str = "palettes"):
        self.storage_dir = storage_dir
        self.data_file = os.path.join(storage_dir, "palettes.json")
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist"""
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_palette(self, palette: Palette) -> None:
        """Save a palette to storage"""
        # Load existing palettes
        palettes = self.load_all_palettes()
        
        # Add or update the palette
        updated = False
        for i, existing in enumerate(palettes):
            if existing.name == palette.name:
                palettes[i] = palette
                updated = True
                break
        
        if not updated:
            palettes.append(palette)
        
        # Save back to file
        with open(self.data_file, 'w') as f:
            json.dump([p.to_dict() for p in palettes], f, indent=2)

    def load_all_palettes(self) -> List[Palette]:
        """Load all palettes from storage"""
        if not os.path.exists(self.data_file):
            return []
        
        with open(self.data_file, 'r') as f:
            data = json.load(f)
            return [Palette.from_dict(p) for p in data]

    def delete_palette(self, name: str) -> None:
        """Delete a palette by name"""
        palettes = self.load_all_palettes()
        palettes = [p for p in palettes if p.name != name]
        
        with open(self.data_file, 'w') as f:
            json.dump([p.to_dict() for p in palettes], f, indent=2) 