#!/usr/bin/env python3
"""
Fetch and process Pokémon data using a pipeline configuration.

This script loads a scope configuration and executes the defined pipeline
to fetch, enrich, and transform Pokémon data.

Usage:
    python scripts/fetch.py --scope pokedex
    python scripts/fetch.py --scope pokedex --dry-run
"""

import argparse
import sys
import yaml
import logging
from pathlib import Path

# Add parent directory to path for lib imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from engine import PipelineEngine, StepRegistry
from steps.fetch_pokeapi_national_dex import FetchPokeAPIStep
from steps.group_by_generation import GroupByGenerationStep
from steps.enrich_metadata import EnrichMetadataStep
from steps.enrich_translations_es_it import EnrichTranslationsESITStep
from steps.enrich_type_translations import EnrichTypeTranslations
from steps.fetch_tcgdex_ex_gen1 import FetchTCGdexClassicExStep
from steps.transform_ex_gen1 import TransformClassicExStep
from steps.validate_pokedex_exists import ValidatePokedexExistsStep
from steps.enrich_names_from_pokedex import EnrichNamesFromPokedexStep
from steps.enrich_section_descriptions import EnrichSectionDescriptionsStep
from steps.enrich_featured_cards import EnrichFeaturedElementsStep
from steps.cache_pokemon_images import CachePokemonImages
from steps.fetch_tcgdex_ex_gen2 import FetchTCGdexBlackWhiteEXStep
from steps.fetch_tcgdex_ex_gen3 import FetchTCGdexScarletVioletEXStep
from steps.transform_ex_gen2 import TransformBlackWhiteEXStep
from steps.transform_ex_gen3 import TransformScarletVioletEXStep
from steps.fetch_tcgdex_set import FetchTCGdexSetStep
from steps.enrich_tcg_names_multilingual import EnrichTCGNamesMultilingualStep
from steps.enrich_tcg_cards_from_pokedex import EnrichTCGCardsFromPokedexStep
from steps.enrich_special_cards import EnrichSpecialCardsStep
from steps.transform_tcg_set import TransformTCGSetStep
from steps.transform_to_sections_format import TransformToSectionsFormatStep
from steps.save_output import SaveOutputStep
from steps.load_local_source import LoadLocalSourceStep
from steps.load_tcg_set import LoadTCGSetStep
from steps.load_ex_cards import LoadExCardsStep
from steps.merge_tcg_supplement import MergeTCGSupplementStep


def get_all_scopes() -> list:
    """Get all available scope names from config directory."""
    config_dir = Path(__file__).parent.parent.parent / "config" / "scopes"
    
    if not config_dir.exists():
        return []
    
    # Find all YAML files and extract scope names
    scopes = []
    for yaml_file in config_dir.glob("*.yaml"):
        scope_name = yaml_file.stem  # filename without .yaml extension
        scopes.append(scope_name)
    
    return sorted(scopes)


def load_config(scope: str) -> dict:
    """Load scope configuration from YAML file."""
    # Look in root config directory
    config_path = Path(__file__).parent.parent.parent / "config" / "scopes" / f"{scope}.yaml"
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def validate_config(config: dict) -> bool:
    """Validate the configuration structure."""
    required_fields = ['scope', 'pipeline', 'target_file']
    
    for field in required_fields:
        if field not in config:
            print(f"❌ Missing required field in config: {field}")
            return False
    
    if not isinstance(config['pipeline'], list):
        print(f"❌ Pipeline must be a list of steps")
        return False
    
    return True


def create_registry() -> StepRegistry:
    """Create and populate the step registry with all available steps."""
    registry = StepRegistry()
    
    # Register source loading steps
    registry.register('load_local_source', LoadLocalSourceStep)
    registry.register('load_tcg_set', LoadTCGSetStep)
    registry.register('load_ex_cards', LoadExCardsStep)
    registry.register('merge_tcg_supplement', MergeTCGSupplementStep)
    
    # Register PokeAPI steps
    registry.register('fetch_pokeapi_national_dex', FetchPokeAPIStep)
    registry.register('group_by_generation', GroupByGenerationStep)
    registry.register('enrich_translations_es_it', EnrichTranslationsESITStep)
    registry.register('enrich_type_translations', EnrichTypeTranslations)
    
    # Register enrichment steps
    registry.register('enrich_metadata', EnrichMetadataStep)
    registry.register('enrich_section_descriptions', EnrichSectionDescriptionsStep)
    registry.register('enrich_featured_cards', EnrichFeaturedElementsStep)
    registry.register('enrich_featured_elements', EnrichFeaturedElementsStep)  # New name, keep old for backward compat
    
    # Register TCG steps
    registry.register('fetch_tcgdex_ex_gen1', FetchTCGdexClassicExStep)
    registry.register('transform_ex_gen1', TransformClassicExStep)
    registry.register('fetch_tcgdex_ex_gen2', FetchTCGdexBlackWhiteEXStep)
    registry.register('transform_ex_gen2', TransformBlackWhiteEXStep)
    registry.register('fetch_tcgdex_ex_gen3', FetchTCGdexScarletVioletEXStep)
    registry.register('transform_ex_gen3', TransformScarletVioletEXStep)
    registry.register('fetch_tcgdex_set', FetchTCGdexSetStep)
    registry.register('enrich_tcg_names_multilingual', EnrichTCGNamesMultilingualStep)
    registry.register('enrich_tcg_cards_from_pokedex', EnrichTCGCardsFromPokedexStep)
    registry.register('enrich_special_cards', EnrichSpecialCardsStep)
    registry.register('transform_tcg_set', TransformTCGSetStep)
    registry.register('transform_to_sections_format', TransformToSectionsFormatStep)
    registry.register('validate_pokedex_exists', ValidatePokedexExistsStep)
    registry.register('enrich_names_from_pokedex', EnrichNamesFromPokedexStep)
    
    # Register caching steps
    registry.register('cache_pokemon_images', CachePokemonImages)
    
    # Register utility steps
    registry.register('save_output', SaveOutputStep)
    
    # TODO: Register more steps as they are implemented
    # registry.register('enrich_from_pokeapi', EnrichPokeAPIStep)
    # etc.
    
    return registry


def main():
    parser = argparse.ArgumentParser(description='Fetch Pokémon data using pipeline')
    parser.add_argument('--scope', required=True, help='Scope name (e.g., pokedex) or "all" for all scopes')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--limit', type=int, help='Limit Pokemon per generation (test mode)')
    parser.add_argument('--generations', type=str, help='Comma-separated list of generations (e.g., 1,2,3)')
    parser.add_argument('--fetch-only', action='store_true', help='Execute only fetch step(s), skip enrichment/transform')
    parser.add_argument('--skip-fetch', action='store_true', help='Skip fetch step(s), run only enrichment/transform from existing source')
    parser.add_argument('--start-from', type=int, help='Start pipeline from step N (1-indexed)')
    parser.add_argument('--stop-after', type=int, help='Stop pipeline after step N (1-indexed)')
    parser.add_argument('--force-featured-cards', action='store_true', help='Force regeneration of featured cards even if they exist')
    
    args = parser.parse_args()
    
    # Handle "all" scope
    if args.scope.lower() == 'all':
        scopes = get_all_scopes()
        
        if not scopes:
            print("❌ No scopes found in config/scopes/")
            sys.exit(1)
        
        # Ensure Pokedex is always first (it's the base for all other scopes)
        if 'Pokedex' in scopes:
            scopes.remove('Pokedex')
            scopes.insert(0, 'Pokedex')
        
        print(f"🔍 Found {len(scopes)} scopes to process:")
        for scope in scopes:
            print(f"   • {scope}")
        
        if args.dry_run:
            print("\n🏃 Dry run mode - not executing")
            return
        
        print(f"\n{'='*80}")
        
        # Process each scope
        failed_scopes = []
        for i, scope in enumerate(scopes, 1):
            print(f"\n[{i}/{len(scopes)}] Processing scope: {scope}")
            print(f"{'='*80}\n")
            
            try:
                success = process_scope(scope, args)
                if not success:
                    failed_scopes.append(scope)
                    print(f"\n⚠️  Scope {scope} failed, continuing with next...")
            except Exception as e:
                print(f"\n❌ Error processing {scope}: {e}")
                failed_scopes.append(scope)
                print(f"⚠️  Continuing with next scope...")
            
            if i < len(scopes):
                print(f"\n{'='*80}")
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📊 Summary:")
        print(f"   Total scopes:    {len(scopes)}")
        print(f"   ✅ Successful:   {len(scopes) - len(failed_scopes)}")
        print(f"   ❌ Failed:       {len(failed_scopes)}")
        
        if failed_scopes:
            print(f"\n⚠️  Failed scopes: {', '.join(failed_scopes)}")
            sys.exit(1)
        
        print(f"{'='*80}")
        return
    
    # Single scope mode
    success = process_scope(args.scope, args)
    
    if not success:
        print("\n❌ Pipeline failed")
        sys.exit(1)


def process_scope(scope: str, args) -> bool:
    """Process a single scope. Returns True on success, False on failure."""
    # Load and validate config
    print(f"📋 Loading scope: {scope}")
    config = load_config(scope)
    
    if not validate_config(config):
        return False
    
    # Apply CLI overrides to config
    if args.limit or args.generations or args.force_featured_cards:
        print(f"🔧 Applying CLI overrides:")
        if args.limit:
            print(f"   --limit {args.limit}")
        if args.generations:
            print(f"   --generations {args.generations}")
        if args.force_featured_cards:
            print('   --force-featured-elements')
        
        # Apply overrides to relevant steps
        for step_config in config['pipeline']:
            step_name = step_config['step']
            params = step_config.get('params', {})
            
            # Apply limit to fetch steps
            if args.limit and 'fetch' in step_name:
                params['limit'] = args.limit
            
            # Apply generations to PokeAPI fetch
            if args.generations and step_name == 'fetch_pokeapi_national_dex':
                gens = [int(g.strip()) for g in args.generations.split(',')]
                params['generations'] = gens
            
            # Apply force to featured cards enrichment
            if args.force_featured_cards and step_name == 'enrich_featured_cards':
                params['force'] = True
            
            step_config['params'] = params
    
    print(f"✅ Config loaded: {config['description']}")
    if 'source_file' in config:
        print(f"📁 Source: {config['source_file']}")
    print(f"📁 Target: {config['target_file']}")
    print(f"🔧 Pipeline steps: {len(config['pipeline'])}")
    
    # Apply step filtering based on CLI arguments
    original_pipeline = config['pipeline'].copy()
    filtered_pipeline = config['pipeline']
    
    if args.fetch_only:
        # Execute only fetch steps (steps with 'fetch' in name)
        filtered_pipeline = [s for s in config['pipeline'] if 'fetch' in s['step'].lower()]
        print(f"🎯 Fetch-only mode: {len(filtered_pipeline)}/{len(original_pipeline)} steps")
    
    elif args.skip_fetch:
        # Skip fetch steps (steps with 'fetch' in name)
        filtered_pipeline = [s for s in config['pipeline'] if 'fetch' not in s['step'].lower()]
        
        # Prepend load_local_source step to load cached source data
        source_file = config.get('source_file', 'data/source/pokedex.json')
        load_source_step = {
            'step': 'load_local_source',
            'params': {'source_file': source_file}
        }
        filtered_pipeline.insert(0, load_source_step)
        
        print(f"⏭️  Skip-fetch mode: {len(filtered_pipeline)}/{len(original_pipeline)} steps")
        print(f"    (includes load_local_source for {source_file})")
    
    elif args.start_from or args.stop_after:
        # Filter by step index
        start_idx = (args.start_from - 1) if args.start_from else 0
        stop_idx = args.stop_after if args.stop_after else len(config['pipeline'])
        filtered_pipeline = config['pipeline'][start_idx:stop_idx]
        print(f"🎯 Step range [{start_idx+1}-{stop_idx}]: {len(filtered_pipeline)}/{len(original_pipeline)} steps")
    
    config['pipeline'] = filtered_pipeline
    
    # Show pipeline
    print("\n📋 Pipeline:")
    for i, step in enumerate(config['pipeline'], 1):
        step_name = step['step']
        params = step.get('params', {})
        param_str = f" with {len(params)} params" if params else ""
        print(f"  {i}. {step_name}{param_str}")
    
    if args.dry_run:
        print("\n🏃 Dry run mode - not executing")
        return True
    
    # Create step registry and pipeline engine
    registry = create_registry()
    engine = PipelineEngine(config, registry)
    
    # Execute pipeline
    success = engine.execute()
    
    if success:
        print(f"\n✅ Pipeline completed successfully!")
        print(f"📄 Output written to: {config['target_file']}")
    
    return success


if __name__ == '__main__':
    main()
