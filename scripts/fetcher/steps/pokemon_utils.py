"""
Pokemon Utility Functions

Shared utility functions for Pokemon data processing across different pipeline steps.
"""

import logging
import re
import requests

logger = logging.getLogger(__name__)


def get_mega_artwork_url(
    pokemon_name: str, 
    base_id: int, 
    form_suffix: str = None,
    original_card_name: str = None
) -> str:
    """
    Get artwork URL for Mega Evolution forms from PokeAPI.
    
    Mega evolutions have special IDs in PokeAPI (e.g., Mega Charizard X = 10034).
    Query PokeAPI to find the correct form ID.
    
    Args:
        pokemon_name: English Pokemon base name (e.g., "Charizard")
        base_id: Base Pokemon ID (e.g., 6 for Charizard)
        form_suffix: Optional explicit form suffix (e.g., "X", "Y")
        original_card_name: Optional TCG card name to extract form suffix from
    
    Returns:
        URL to the exact form-specific artwork

    Raises:
        RuntimeError: If PokeAPI cannot resolve the requested form.  Returning
            base artwork here would silently change the poster subject.
    """
    # If form_suffix not provided, try to extract from original_card_name
    if form_suffix is None and original_card_name:
        # Extract X or Y suffix from original card name
        # Examples: "Mega Charizard X ex" -> "x", "Mega Lopunny ex" -> None
        if ' X ' in original_card_name or original_card_name.endswith(' X'):
            form_suffix = 'x'
        elif ' Y ' in original_card_name or original_card_name.endswith(' Y'):
            form_suffix = 'y'
    
    # Normalize form_suffix to lowercase
    if form_suffix:
        form_suffix = form_suffix.lower()
    
    # For Mega Evolutions, need to fetch the form-specific Pokemon ID
    try:
        # Construct form name: "charizard-mega-x" or "lopunny-mega"
        base_name = pokemon_name.strip()
        if form_suffix:
            # The exact TCG title may already retain the X/Y form marker
            # ("Charizard X").  PokeAPI places that marker after "mega", so
            # remove it from the species portion before composing the slug.
            base_name = re.sub(
                rf"(?:[\s-]+{re.escape(form_suffix)})$",
                "",
                base_name,
                flags=re.IGNORECASE,
            )
        base_name = base_name.lower().replace(' ', '-')
        form_name = f"{base_name}-mega"
        if form_suffix:
            form_name += f"-{form_suffix}"
        
        # Query PokeAPI for this form
        response = requests.get(f"https://pokeapi.co/api/v2/pokemon/{form_name}", timeout=10)
        if response.status_code == 200:
            form_data = response.json()
            form_id = form_data.get('id')
            if form_id:
                logger.debug(f"Found Mega form ID {form_id} for {form_name}")
                return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{form_id}.png"
        
        raise RuntimeError(
            f"PokeAPI did not resolve the requested form {form_name!r}"
        )
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(
            f"Could not resolve exact PokeAPI artwork for {form_name!r}: {e}"
        ) from e
