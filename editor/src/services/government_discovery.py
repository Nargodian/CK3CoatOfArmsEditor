"""Service for discovering government types from asset files"""
from pathlib import Path
from utils.path_resolver import get_resource_path


class GovernmentDiscovery:
	"""Discovers available government types from realm_frames directory"""
	
	@staticmethod
	def get_government_types():
		"""Discover government types from realm_frames mask files
		
		Returns:
			tuple: (government_list, government_file_map) where
				government_list is list of display names
				government_file_map is dict of display_name -> file_key
		"""
		try:
			realm_frames_dir = get_resource_path('..', 'ck3_assets', 'realm_frames')
			if not Path(realm_frames_dir).exists():
				return _get_default_governments()
			
			governments = []
			government_file_map = {}
			
			for mask_file in sorted(Path(realm_frames_dir).glob("*_mask.png")):
				gov_key = mask_file.stem.replace("_mask", "")
				display_name = _convert_to_display_name(gov_key)
				governments.append(display_name)
				government_file_map[display_name] = gov_key
			
			return governments if governments else _get_default_governments()
		
		except Exception as e:
			print(f"Error discovering governments: {e}")
			return _get_default_governments()


def _get_default_governments():
	"""Fallback government list"""
	return (["Feudal", "Clan"], {"Feudal": "_default", "Clan": "clan_government"})


def _convert_to_display_name(gov_key):
	"""Convert filename key to display name"""
	if gov_key == "_default":
		return "Feudal"
	# Remove _government suffix and convert to title case
	return gov_key.replace("_government", "").replace("_", " ").title()
