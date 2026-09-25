"""Job-local P16 ComfyUI node mapping."""
from __future__ import annotations

from .guider import create_guider


class RegionConstrainedJointGuider:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "model": ("MODEL",),
            "global_conditioning": ("CONDITIONING",),
            "left_conditioning": ("CONDITIONING",),
            "right_conditioning": ("CONDITIONING",),
            "region_contract": ("STRING", {"multiline": True}),
        }}

    RETURN_TYPES = ("GUIDER",)
    FUNCTION = "create"
    CATEGORY = "sampling/custom_sampling/guiders"

    def create(self, model, global_conditioning, left_conditioning, right_conditioning, region_contract):
        return (create_guider(model, global_conditioning, left_conditioning, right_conditioning, region_contract),)


NODE_CLASS_MAPPINGS = {"RegionConstrainedJointGuider": RegionConstrainedJointGuider}
