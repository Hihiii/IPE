export class WardrobeMaterialSystem {
  constructor() {
    this.name = "07_wardrobe_material_system";
  }

  process(rawPrompt, capsule) {
    const raw = rawPrompt.toLowerCase();
    const materials = capsule?.materials || {};
    const policy = capsule?.policy || {};
    const slots = capsule?.slots || [];
    const foundMaterials = [];

    for (const [mat, desc] of Object.entries(materials)) {
      if (raw.includes(mat)) {
        foundMaterials.push({ material: mat, description: desc });
      }
    }

    const explicitItems = this._extractExplicitItems(raw, slots);

    return {
      autoFillProhibited: policy.auto_fill_prohibited !== false,
      explicitItems,
      absentSlots: slots.filter((s) => !explicitItems.includes(s)),
      foundMaterials,
      canonicalTriggerRequired: policy.canonical_costume_trigger_required !== false,
      hasCanonicalTrigger: this._hasCanonicalTrigger(raw, policy),
    };
  }

  _extractExplicitItems(raw, slots) {
    const found = [];
    const itemKeywords = {
      headwear: ["hat", "cap", "headband", "crown", "hood", "helmet", "beret"],
      top: ["shirt", "blouse", "top", "t-shirt", "tank top", "crop top", "turtleneck", "sweater", "hoodie", "jacket", "coat", "vest", "blazer", "cardigan", "bra", "bikini top"],
      bottom: ["pants", "jeans", "trousers", "shorts", "skirt", "leggings", "sweatpants", "hot pants", "trunks", "panties", "thong", "bikini bottom"],
      dress: ["dress", "gown", "sundress", "maxi dress", "mini dress", "cocktail dress", "slip dress", "robe", "kimono", "nightgown", "caftan"],
      outerwear: ["jacket", "coat", "blazer", "cardigan", "hoodie", "sweater", "poncho", "cape", "cloak", "raincoat", "leather jacket", "denim jacket"],
      footwear: ["shoes", "boots", "heels", "sneakers", "sandals", "flats", "stilettos", "pumps", "loafers", "wedges", "platforms"],
      accessories: ["belt", "scarf", "tie", "glasses", "sunglasses", "necklace", "earrings", "ring", "bracelet", "watch", "bag", "purse", "backpack", "hat", "gloves", "choker"],
      undergarments: ["underwear", "bra", "panties", "thong", "boxers", "briefs", "bikini", "lingerie", "teddy", "corset", "garter", "stockings", "tights", "pantyhose", "suspender"],
    };

    for (const [slot, keywords] of Object.entries(itemKeywords)) {
      for (const kw of keywords) {
        if (raw.includes(kw)) {
          found.push(slot);
          break;
        }
      }
    }

    return [...new Set(found)];
  }

  _hasCanonicalTrigger(raw, policy) {
    const triggers = policy.trigger_keywords || ["canonical", "cosplay", "original_outfit", "source_accurate"];
    return triggers.some((t) => raw.includes(t));
  }
}
