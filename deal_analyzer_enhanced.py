
import argparse
import json
import math
import re
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, TypedDict
from collections import defaultdict


class PriceDict(TypedDict, total=False):
    amount: Optional[float]
    unit: Optional[str]
    display: Optional[str]
    is_multibuy: Optional[bool]
    multibuy_details: Optional[dict]
    original_price: Optional[float]
    savings_amount: Optional[float]
    savings_percent: Optional[float]


class DealDict(TypedDict, total=False):
    deal_id: Any
    page: Any
    retailer: Optional[str]
    product_name: Optional[str]
    brand: Optional[str]
    category: Optional[str]
    price: PriceDict
    size_quantity: Optional[str]
    container_type: Optional[str]
    conditions: Dict[str, Any]
    promotion_type: Optional[str]
    promotion_group_id: Optional[str]
    special_notes: Optional[str]
    extraction_confidence: Optional[str]
    uncertainty_flags: List[str]


@dataclass
class DealAnalyzerConfig:
    """Configuration holder so keywords/weights can evolve without editing code logic."""

    # Store brands to exclude
    store_brands: List[str] = field(default_factory=lambda: [
        # Amazon/Whole Foods
        "Amazon Grocery", "Amazon Kitchen", "Amazon Fresh",
        "365 Brand", "365 by Whole Foods", "365 Everyday Value",

        # Major chains
        "Kirkland", "Great Value", "Market Pantry", "Simple Truth",
        "O Organics", "Kroger", "Target", "Safeway SELECT",

        # Smart & Final
        "First Street",

        # HEB brands
        "H-E-B", "Hill Country Fare", "Central Market", "Higher Harvest",
        "HEB",

        # Sprouts brands
        "Sprouts", "Real Root by Sprouts", "Sprouts Farmers Market",

        # Other regional
        "Albertsons", "Vons", "Pavilions", "Ralphs", "Food Lion"
    ])

    excluded_categories: List[str] = field(default_factory=lambda: [
        "Beer, Wine & Spirits",
        "ALCOHOL",
        "BEVERAGES_ALCOHOL"
    ])

    supplement_keywords: List[str] = field(default_factory=lambda: [
        "supplement", "vitamin", "pill", "capsule",
        "tablet", "probiotic", "greens powder", "protein powder",
        "multivitamin", "omega-3", "turmeric", "ashwagandha",
        "collagen", "magnesium", "zinc", "elderberry"
    ])

    excluded_products: List[str] = field(default_factory=lambda: [
        "hot dog", "hotdog", "hot dogs", "hotdogs",
        "franks", "wiener", "wieners"
    ])

    priority_deals: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "chicken_breast": {
            "keywords": ["chicken breast", "chicken thigh", "chicken thighs"],
            "exclude_keywords": ["boneless skinless chicken breast meal", "rotisserie"],
            "max_price_per_lb": 3.00,
            "category": ["MEAT", "Meat", "Meat & Seafood"],
            "bonus_score": 30
        },
        "steak": {
            "keywords": ["steak", "ribeye", "sirloin", "ny strip", "t-bone",
                        "porterhouse", "flank", "skirt", "filet"],
            "exclude_keywords": ["salisbury", "patties", "burger"],
            "max_price_per_lb": 10.00,
            "category": ["MEAT", "Meat", "Meat & Seafood"],
            "bonus_score": 25
        },
        "ground_beef": {
            "keywords": ["ground beef", "ground chuck", "hamburger"],
            "exclude_keywords": ["patties", "burger patty", "ground turkey"],
            "max_price_per_lb": 6.00,
            "category": ["MEAT", "Meat", "Meat & Seafood"],
            "bonus_score": 20
        }
    })

    premium_keywords: set = field(default_factory=lambda: {
        # Meat
        "ribeye", "prime rib", "flank steak", "sirloin", "filet mignon",
        "ny strip", "porterhouse", "wagyu", "angus", "grass-fed",
        "organic chicken", "air-chilled", "heritage pork",

        # Seafood
        "salmon", "atlantic salmon", "king salmon", "sockeye",
        "shrimp", "jumbo shrimp", "scallops", "crab", "lobster",
        "halibut", "sea bass", "ahi tuna", "swordfish",

        # Produce
        "honeycrisp", "cotton candy grape", "dekopon", "sumo citrus",
        "organic", "heirloom", "persimmon", "dragon fruit",
        "artisan", "specialty mushroom", "truffle"
    })

    viral_keywords: set = field(default_factory=lambda: {
        "cotton candy", "party pack", "family size", "jumbo", "giant",
        "mega", "ultimate", "variety pack", "assorted", "party size",
        "super bowl", "game day", "tailgate", "celebration",
        "viral", "tiktok", "trending"
    })

    major_brands: set = field(default_factory=lambda: {
        # Snacks
        "doritos", "lays", "cheetos", "fritos", "ruffles", "tostitos",
        "pringles", "kettle", "popchips", "smartfood", "pirates booty",

        # Beverages
        "coca-cola", "coke", "pepsi", "sprite", "mountain dew",
        "dr pepper", "7up", "canada dry", "schweppes", "crush",
        "capri sun", "gatorade", "powerade", "vitamin water",

        # Chocolate/Candy
        "hershey", "reese's", "kit kat", "m&m", "snickers", "twix",
        "milky way", "skittles", "starburst", "sour patch", "haribo",

        # Frozen
        "ben & jerry", "breyer", "haagen-dazs", "talenti", "outshine",
        "drumstick", "klondike", "good humor", "magnum",

        # Dairy
        "dannon", "chobani", "yoplait", "fage", "siggi", "oikos",
        "tillamook", "kerrygold", "organic valley", "horizon",

        # Meat/Protein
        "tyson", "perdue", "foster farms", "applegate", "hormel",
        "oscar mayer", "hillshire farm", "jimmy dean", "butterball",

        # Pantry/Packaged
        "kraft", "philadelphia", "velveeta", "barilla", "prego",
        "ragu", "newman's own", "rao's", "classico", "bertolli",
        "general mills", "kellogg", "quaker", "post", "nabisco",
        "oreo", "chips ahoy", "ritz", "triscuit", "wheat thins",
        "dave's killer bread", "artesano", "bimbo",

        # Natural/Organic
        "annie's", "stonyfield", "nature's path", "kashi",
        "amy's", "dr praeger", "gardein", "beyond meat"
    })

    category_weights: Dict[str, int] = field(default_factory=lambda: {
        # Meat (highest engagement)
        "MEAT": 25,
        "Meat": 25,
        "Meat & Seafood": 25,
        "SEAFOOD": 25,
        "Seafood": 25,
        "DELI": 20,
        "Deli": 20,

        # Produce (highest engagement)
        "PRODUCE": 25,
        "Produce": 25,
        "Fresh Produce": 25,
        "Organic Produce": 25,

        # Snacks & Beverages (high engagement)
        "SNACKS": 20,
        "Snacks": 20,
        "BEVERAGES": 20,
        "Beverages": 20,
        "Drinks": 20,

        # Frozen (medium-high)
        "FROZEN": 15,
        "Frozen": 15,
        "Frozen Foods": 15,
        "Ice Cream": 18,

        # Prepared Foods (medium-high)
        "PREPARED_FOODS": 15,
        "Prepared Foods": 15,
        "Ready to Eat": 15,

        # Dairy & Eggs (medium)
        "DAIRY_EGGS": 12,
        "Dairy": 12,
        "Dairy & Eggs": 12,

        # Bakery (medium)
        "BAKERY": 12,
        "Bakery": 12,
        "Commercial Bakery": 10,
        "Fresh Bakery": 12,

        # Pantry (lower)
        "PANTRY": 10,
        "Pantry": 10,
        "Grocery": 10,
        "Canned Goods": 8,

        # Household (lowest)
        "HOUSEHOLD": 5,
        "Household": 5,
        "Cleaning": 5,
        "Paper Products": 5,

        # Health & Beauty (lowest)
        "HEALTH_BEAUTY": 5,
        "Health & Beauty": 5,
        "Personal Care": 5,

        # Pet (low)
        "PET": 5,
        "Pet": 5,
        "Pet Supplies": 5
    })

    # Behavior toggles
    dedupe: bool = True
    balance_categories: bool = True


class DealAnalyzer:
    """
    Enhanced Deal Analyzer for multiple retailers
    Supports: HEB, Smart & Final, Sprouts, Amazon Fresh, Whole Foods

    Backwards compatible with the existing GUI usage:
      analyzer = DealAnalyzer(retailer_filter="AMAZON_FRESH")
      top = analyzer.analyze_deals(deals, top_n=6)
      print(analyzer.format_output(top, show_details=True))
    """

    # Keep legacy constants for backwards compatibility / external references.
    STORE_BRANDS = DealAnalyzerConfig().store_brands
    EXCLUDED_CATEGORIES = DealAnalyzerConfig().excluded_categories
    SUPPLEMENT_KEYWORDS = DealAnalyzerConfig().supplement_keywords
    EXCLUDED_PRODUCTS = DealAnalyzerConfig().excluded_products
    PRIORITY_DEALS = DealAnalyzerConfig().priority_deals
    PREMIUM_KEYWORDS = DealAnalyzerConfig().premium_keywords
    VIRAL_KEYWORDS = DealAnalyzerConfig().viral_keywords
    MAJOR_BRANDS = DealAnalyzerConfig().major_brands
    CATEGORY_WEIGHTS = DealAnalyzerConfig().category_weights

    
    def _extract_multibuy_details(self, deal: DealDict) -> Tuple[Optional[float], Optional[int], Optional[float], Optional[str]]:
        """Extract multibuy per-unit info when present.

        Returns:
            (per_unit_cost, quantity_required, total_cost, format_str)
        """
        price = (deal.get("price") or {})
        if not price.get("is_multibuy"):
            return (None, None, None, None)

        details = price.get("multibuy_details")
        if not isinstance(details, dict):
            return (None, None, None, None)

        per_unit = details.get("per_unit_cost")
        qty_req = details.get("quantity_required")
        total = details.get("total_cost")
        fmt = details.get("format")

        try:
            per_unit_f = float(per_unit) if per_unit is not None else None
        except Exception:
            per_unit_f = None

        try:
            qty_i = int(qty_req) if qty_req is not None else None
        except Exception:
            qty_i = None

        try:
            total_f = float(total) if total is not None else None
        except Exception:
            total_f = None

        fmt_s = str(fmt) if fmt is not None else None
        return (per_unit_f, qty_i, total_f, fmt_s)

    def _apply_multibuy_overrides(self, deal: DealDict) -> DealDict:
        """Return a shallow-copied deal with multibuy per-unit price applied (for scoring + display)."""
        per_unit, qty_req, total, fmt = self._extract_multibuy_details(deal)
        if per_unit is None or qty_req is None:
            return deal

        deal_copy: DealDict = dict(deal)
        price = dict((deal.get("price") or {}))
        unit = price.get("unit") or "ea"
        # Normalize common each variants for display
        unit_disp = "ea" if str(unit).lower() in {"ea", "each"} else str(unit)

        price["amount"] = per_unit
        price["display"] = f"${per_unit:.2f} {unit_disp}"
        deal_copy["price"] = price

        # Surface quantity_required + format at top-level for existing formatter
        deal_copy["quantity_required"] = qty_req
        if fmt and not deal_copy.get("format"):
            deal_copy["format"] = fmt

        # Keep helpful multibuy metadata for email rendering
        deal_copy["multibuy_total_cost"] = total
        deal_copy["multibuy_format"] = fmt
        return deal_copy
    def __init__(
        self,
        retailer_filter: Optional[str] = None,
        config: Optional[DealAnalyzerConfig] = None
    ):
        """
        Initialize analyzer

        Args:
            retailer_filter: Optional retailer name to filter by (e.g., "HEB", "SPROUTS")
            config: Optional DealAnalyzerConfig override
        """
        self.retailer_filter = retailer_filter
        self.config = config or DealAnalyzerConfig()

        # Pre-compile store brand matchers (word-boundary-ish) to reduce false positives.
        self._store_brand_patterns: List[re.Pattern] = []
        for b in self.config.store_brands:
            b_clean = re.escape(b.strip())
            if not b_clean:
                continue
            # Match on word boundaries when possible, but allow punctuation within the phrase.
            # Example: "H-E-B" or "365 Brand"
            pat = re.compile(rf"(?<!\w){b_clean}(?!\w)", re.IGNORECASE)
            self._store_brand_patterns.append(pat)

    # -------------------------
    # Normalization helpers
    # -------------------------
    _RE_NUM = re.compile(r"(\d+(?:\.\d+)?)")

    def _parse_display_unit(self, display: str) -> Optional[str]:
        d = (display or "").lower()
        if "per lb" in d or "/lb" in d:
            return "lb"
        if "per pound" in d:
            return "lb"
        if "per oz" in d or "/oz" in d:
            return "oz"
        if "per fl oz" in d or "per floz" in d or "/fl oz" in d:
            return "floz"
        if "each" in d and "per" in d:
            return "each"
        return None

    def normalize_unit(self, unit: Optional[str], display: Optional[str] = None) -> Tuple[str, Optional[float], str]:
        """
        Normalize unit strings into a (kind, quantity_in_kind, canonical_kind) tuple.

        Returns:
            kind: one of 'lb','floz','each','count','unknown'
            qty:  numeric quantity for the unit (e.g., 3 for '3lb', 4 for '4count')
            canonical_kind: canonical base for pricing comparisons: 'lb','floz','each','count','unknown'
        """
        u = (unit or "").strip().lower()

        # If unit is missing, attempt to infer from display.
        if not u and display:
            inferred = self._parse_display_unit(display)
            if inferred:
                u = inferred

        if not u:
            return ("unknown", None, "unknown")

        # Common synonyms
        if u in {"lb", "lbs", "pound", "pounds"}:
            return ("lb", 1.0, "lb")

        # Numeric-prefixed patterns
        m = self._RE_NUM.match(u)
        if m:
            num = float(m.group(1))
            tail = u[m.end():].strip()
            tail = tail.replace(" ", "")

            if tail in {"lb", "lbs", "pound", "pounds"}:
                return ("lb", num, "lb")
            if tail in {"oz"}:
                # Treat oz as weight; canonical base is lb.
                # qty returned in oz for clarity.
                return ("oz", num, "lb")
            if tail in {"floz", "fl.oz", "fl-oz", "fl oz"}:
                return ("floz", num, "floz")
            if tail in {"count", "ct"}:
                return ("count", num, "count")

        # Non-numeric tokens
        if "floz" in u or "fl oz" in u:
            # Try to extract number.
            m2 = self._RE_NUM.search(u)
            return ("floz", float(m2.group(1)) if m2 else None, "floz")
        if "count" in u or u in {"ct"}:
            m2 = self._RE_NUM.search(u)
            return ("count", float(m2.group(1)) if m2 else None, "count")
        if u in {"each", "ea"}:
            return ("each", 1.0, "each")

        # Pack/bag is effectively "each" for scoring unless we can extract a count elsewhere.
        if u in {"pack", "bag", "pkg"}:
            return ("each", 1.0, "each")

        return ("unknown", None, "unknown")

    def compute_unit_price(self, deal: DealDict) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """
        Compute a comparable unit price when possible.

        Returns:
            (unit_price_amount, unit_price_unit, unit_price_display)
        """
        deal = self._apply_multibuy_overrides(deal)
        price = (deal.get("price") or {})
        amount = price.get("amount")
        if amount is None or not isinstance(amount, (int, float)) or math.isnan(float(amount)):
            return (None, None, None)

        unit = price.get("unit")
        display = price.get("display")
        kind, qty, canonical = self.normalize_unit(unit, display)

        if canonical == "lb":
            if kind == "lb" and qty and qty > 0:
                up = float(amount) / float(qty)
                return (up, "lb", f"${up:.2f}/lb")
            if kind == "oz" and qty and qty > 0:
                # qty oz -> qty/16 lb
                up = float(amount) / (float(qty) / 16.0)
                return (up, "lb", f"${up:.2f}/lb")
            # If we inferred lb but don't have qty, treat as per-lb.
            if kind == "lb" and (qty is None or qty == 0):
                return (float(amount), "lb", f"${float(amount):.2f}/lb")

        if canonical == "floz":
            if qty and qty > 0:
                up = float(amount) / float(qty)
                return (up, "fl oz", f"${up:.2f}/fl oz")
            # If unit says "floz" without qty, can't compute.
            return (None, None, None)

        if canonical in {"each", "count"}:
            if qty and qty > 0:
                up = float(amount) / float(qty)
                unit_label = "each" if canonical == "each" else "count"
                return (up, unit_label, f"${up:.2f} ea" if unit_label=="each" else f"${up:.2f}/{unit_label}")
            # If "each" with no qty, assume per item.
            if canonical == "each":
                return (float(amount), "each", f"${float(amount):.2f} ea")

        return (None, None, None)

    # -------------------------
    # Exclusion logic + reasons
    # -------------------------
    def get_exclusion_reason(self, deal: DealDict) -> Optional[str]:
        """Return a short reason string if excluded, else None."""
        price_amount = (deal.get("price") or {}).get("amount")

        # Exclude if no price or price is null / non-numeric
        if price_amount is None or not isinstance(price_amount, (int, float)):
            return "missing_price_amount"
        if isinstance(price_amount, (int, float)) and price_amount < 0:
            return "invalid_negative_price"

        category = deal.get("category") or ""
        cat_u = category.upper()

        # Exclude alcohol categories (robust)
        if category in self.config.excluded_categories:
            return "excluded_category_alcohol"
        if any(token in cat_u for token in ["ALCOHOL", "BEER", "WINE", "SPIRITS"]):
            # Keeps prior behavior but catches variants like "Beer & Wine"
            return "excluded_category_alcohol"

        # Exclude supplements from Health & Beauty
        if "HEALTH" in cat_u or "BEAUTY" in cat_u:
            product_name = (deal.get("product_name") or "").lower()
            if any(keyword in product_name for keyword in self.config.supplement_keywords):
                return "excluded_supplement"

        product_name = deal.get("product_name") or ""
        brand = deal.get("brand") or ""
        combined_l = f"{product_name} {brand}".lower()

        # Exclude store brands (prefer exact brand matches; then phrase matches)
        brand_l = brand.lower().strip()
        for b in self.config.store_brands:
            if brand_l and brand_l == b.lower():
                return "excluded_store_brand"
        for pat in self._store_brand_patterns:
            if pat.search(combined_l):
                return "excluded_store_brand"

        # Exclude specific products (category-aware for ambiguous terms)
        product_lower = product_name.lower()
        if any(excl in product_lower for excl in self.config.excluded_products):
            # Only apply to likely relevant categories (avoid accidental brand/name collisions)
            if any(tok in cat_u for tok in ["MEAT", "DELI", "SEAFOOD"]):
                return "excluded_product_keyword"

        # Apply retailer filter if set
        if self.retailer_filter and deal.get("retailer") != self.retailer_filter:
            return "filtered_out_by_retailer"

        return None

    def should_exclude(self, deal: DealDict) -> bool:
        return self.get_exclusion_reason(deal) is not None

    # -------------------------
    # Priority deals
    # -------------------------
    def is_priority_deal(self, deal: DealDict) -> bool:
        """
        Check if deal meets priority criteria (auto-include).
        Priority deals are based on *price per lb* (normalized).
        """
        product_name = (deal.get("product_name") or "").lower()
        category = deal.get("category") or ""

        unit_price_amount, unit_price_unit, _ = self.compute_unit_price(deal)
        if unit_price_unit != "lb" or unit_price_amount is None:
            return False

        for _, criteria in self.config.priority_deals.items():
            if category not in criteria["category"]:
                continue
            if unit_price_amount > criteria["max_price_per_lb"]:
                continue
            if not any(keyword in product_name for keyword in criteria["keywords"]):
                continue
            if any(excl in product_name for excl in criteria.get("exclude_keywords", [])):
                continue
            return True

        return False

    def get_priority_bonus(self, deal: DealDict) -> int:
        if not self.is_priority_deal(deal):
            return 0

        product_name = (deal.get("product_name") or "").lower()
        for _, criteria in self.config.priority_deals.items():
            has_keyword = any(keyword in product_name for keyword in criteria["keywords"])
            has_exclusion = any(excl in product_name for excl in criteria.get("exclude_keywords", []))
            if has_keyword and not has_exclusion:
                return int(criteria.get("bonus_score", 0))
        return 0

    # -------------------------
    # Scoring components
    # -------------------------
    def _effective_price_for_scoring(self, deal: DealDict) -> float:
        """
        Use a comparable unit price when available (e.g., $4.99 per 3lb -> $1.66/lb),
        otherwise fall back to the raw amount.
        """
        deal_eff = self._apply_multibuy_overrides(deal)
        price_amount = float((deal_eff.get("price") or {}).get("amount") or 0.0)
        deal_for_unit = deal_eff
        up, up_unit, _ = self.compute_unit_price(deal_for_unit)
        if up is None or up_unit is None:
            return price_amount
        # For scoring, unit prices are better indicators than package prices.
        return float(up)

    def calculate_viral_pricing_score(self, deal: DealDict) -> int:
        """Calculate viral pricing bonus (0-30 points) using effective comparable price where possible."""
        score = 0
        price_eff = self._effective_price_for_scoring(deal)

        # Under $1 is extremely viral
        if price_eff < 1.00:
            score += 30
        elif price_eff <= 2.99:
            score += 20
        elif price_eff <= 4.99:
            score += 10

        # Round-number pricing bonus (still based on displayed price amount)
        raw_amount = (deal.get("price") or {}).get("amount")
        if isinstance(raw_amount, (int, float)):
            price_str = f"{float(raw_amount):.2f}"
            if any(price_str.endswith(ending) for ending in ["0.99", "1.99", "2.49", "2.99", "4.99", "9.99"]):
                score += 8  # slightly reduced to avoid overpowering real value

        # Multi-buy bonus
        if (deal.get("price") or {}).get("is_multibuy"):
            score += 15

        # High savings percentage (kept, but discount depth is handled separately too)
        savings_pct = (deal.get("price") or {}).get("savings_percent")
        if isinstance(savings_pct, (int, float)):
            if savings_pct >= 50:
                score += 12
            elif savings_pct >= 30:
                score += 8

        return min(score, 30)

    def calculate_discount_depth(self, deal: DealDict) -> int:
        """Add a separate discount-depth signal (0-20 points)."""
        price = (deal.get("price") or {})
        savings_pct = price.get("savings_percent")
        orig = price.get("original_price")
        amt = price.get("amount")

        score = 0

        if isinstance(savings_pct, (int, float)):
            # Map 10%->2, 25%->8, 40%->14, 60%->20
            score = int(min(20, max(0, (float(savings_pct) - 5) * (20 / 55))))
            return score

        # If original_price exists but savings_pct doesn't, infer
        if isinstance(orig, (int, float)) and isinstance(amt, (int, float)) and orig > 0 and amt >= 0:
            inferred_pct = (orig - amt) / orig * 100.0
            score = int(min(20, max(0, (inferred_pct - 5) * (20 / 55))))
            return score

        return 0

    def calculate_category_weight(self, deal: DealDict) -> int:
        category = deal.get("category", "") or ""
        return int(self.config.category_weights.get(category, 5))

    def calculate_premium_value(self, deal: DealDict) -> int:
        product_name = (deal.get("product_name") or "").lower()
        special_notes = (deal.get("special_notes") or "").lower()
        brand = (deal.get("brand") or "").lower()
        combined = f"{product_name} {special_notes} {brand}"

        # Check for premium items
        for keyword in self.config.premium_keywords:
            if keyword in combined:
                return 25

        # Popular snack brands
        popular_snacks = ["doritos", "hershey", "outshine", "ben & jerry", "reese's"]
        if any(brand_name in combined for brand_name in popular_snacks):
            return 20

        # Organic
        if "organic" in combined:
            return 18

        # Name brand with discount
        savings_pct = (deal.get("price") or {}).get("savings_percent")
        if isinstance(savings_pct, (int, float)) and savings_pct >= 30:
            return 15

        return 5

    def calculate_social_appeal(self, deal: DealDict) -> int:
        product_name = (deal.get("product_name") or "").lower()
        special_notes = (deal.get("special_notes") or "").lower()
        combined = f"{product_name} {special_notes}"

        for keyword in self.config.viral_keywords:
            if keyword in combined:
                return 20

        interesting_keywords = [
            "cotton candy", "dekopon", "sumo", "dumpling", "truffle",
            "artisan", "heritage", "heirloom", "specialty", "gourmet"
        ]
        if any(keyword in combined for keyword in interesting_keywords):
            return 18

        kid_keywords = [
            "chicken nugget", "drumstick", "popsicle", "fruit bar",
            "cookie", "mac and cheese", "pizza", "lunchable"
        ]
        if any(keyword in combined for keyword in kid_keywords):
            return 12

        meal_keywords = ["entrée", "meal", "dinner", "ready to eat", "prepared"]
        if any(keyword in combined for keyword in meal_keywords):
            return 10

        party_keywords = ["party", "entertaining", "celebration", "game day"]
        if any(keyword in combined for keyword in party_keywords):
            return 15

        return 5

    def calculate_brand_recognition(self, deal: DealDict) -> int:
        product_name = (deal.get("product_name") or "").lower()
        brand = (deal.get("brand") or "").lower()
        combined = f"{product_name} {brand}"

        for brand_name in self.config.major_brands:
            if brand_name in combined:
                return 10

        regional_brands = ["boar's head", "tillamook", "kerrygold", "dave's killer"]
        if any(brand_name in combined for brand_name in regional_brands):
            return 8

        return 5

    def calculate_total_score(self, deal: DealDict) -> int:
        score = 0
        score += self.calculate_viral_pricing_score(deal)
        score += self.calculate_discount_depth(deal)
        score += self.calculate_category_weight(deal)
        score += self.calculate_premium_value(deal)
        score += self.calculate_social_appeal(deal)
        score += self.calculate_brand_recognition(deal)
        score += self.get_priority_bonus(deal)
        return int(score)

    def categorize_deal(self, deal: DealDict) -> str:
        category = (deal.get("category", "") or "").upper()
        if "MEAT" in category or "SEAFOOD" in category or "DELI" in category:
            return "Meat/Seafood"
        if "PRODUCE" in category:
            return "Produce"
        return "Snacks/Other"

    # -------------------------
    # Main analysis
    # -------------------------
    def _dedupe_deals(self, deals: List[DealDict]) -> List[DealDict]:
        if not self.config.dedupe:
            return deals

        seen = set()
        out: List[DealDict] = []
        for d in deals:
            price = d.get("price") or {}
            key = (
                (d.get("retailer") or "").strip().upper(),
                (d.get("product_name") or "").strip().lower(),
                (d.get("category") or "").strip().upper(),
                str(price.get("display") or "").strip(),
                str(price.get("amount")),
                str(price.get("unit")),
                str(d.get("size_quantity") or "").strip().lower(),
                str(d.get("page"))
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(d)
        return out

    def analyze_deals(
        self,
        deals: List[DealDict],
        top_n: int = 6,
        balance_categories: Optional[bool] = None
    ) -> List[DealDict]:
        """
        Analyze all deals and return top N with category balance.
        Priority deals are always included when they qualify.

        Args:
            deals: List of deal dictionaries
            top_n: Number of top deals to return (default 6)
            balance_categories: override config.balance_categories for this run

        Returns:
            List of top scored deals with engagement scores and extra normalized fields
        """
        deals = self._dedupe_deals(deals)
        if not deals:
            return []

        balance = self.config.balance_categories if balance_categories is None else balance_categories

        deals = self._dedupe_deals(deals)

        scored_deals: List[DealDict] = []
        priority_deals: List[DealDict] = []

        for deal in deals:
            deal_eff = self._apply_multibuy_overrides(deal)
            if self.should_exclude(deal_eff):
                continue

            score = self.calculate_total_score(deal_eff)
            deal_copy: DealDict = dict(deal_eff)
            if deal_copy.get("price"):
                deal_copy["price"] = dict(deal_copy["price"])  # avoid mutating input
            deal_copy["engagement_score"] = score
            deal_copy["category_group"] = self.categorize_deal(deal)
            deal_copy["is_priority"] = self.is_priority_deal(deal)

            up_amt, up_unit, up_disp = self.compute_unit_price(deal)
            deal_copy["unit_price_amount"] = up_amt
            deal_copy["unit_price_unit"] = up_unit
            deal_copy["unit_price_display"] = up_disp

            if deal_copy["is_priority"]:
                priority_deals.append(deal_copy)
            else:
                scored_deals.append(deal_copy)

        if not scored_deals and not priority_deals:
            return []

        def tie_break_key(d: DealDict):
            # Higher score first, priority first, higher savings %, lower unit price, lower raw price
            price = d.get("price") or {}
            savings_pct = price.get("savings_percent")
            savings_pct_v = float(savings_pct) if isinstance(savings_pct, (int, float)) else -1.0
            up = d.get("unit_price_amount")
            up_v = float(up) if isinstance(up, (int, float)) else float("inf")
            amt = price.get("amount")
            amt_v = float(amt) if isinstance(amt, (int, float)) else float("inf")
            return (
                -int(d.get("engagement_score", 0)),
                -int(1 if d.get("is_priority") else 0),
                -savings_pct_v,
                up_v,
                amt_v
            )

        scored_deals.sort(key=tie_break_key)
        priority_deals.sort(key=tie_break_key)

        # Start with priority deals (must include)
        top_deals: List[DealDict] = priority_deals.copy()
        remaining_slots = max(0, top_n - len(top_deals))
        if remaining_slots <= 0:
            return top_deals[:top_n]

        if not balance:
            top_deals.extend(scored_deals[:remaining_slots])
            return top_deals[:top_n]

        # Group scored deals by category group
        category_groups: Dict[str, List[DealDict]] = defaultdict(list)
        for d in scored_deals:
            category_groups[str(d.get("category_group"))].append(d)

        # Determine which categories have inventory
        categories = ["Meat/Seafood", "Produce", "Snacks/Other"]
        available_counts = {c: len(category_groups.get(c, [])) for c in categories}
        total_available = sum(available_counts.values())

        # If one bucket has nothing, proportional allocation will naturally skip it.
        allocations = {c: 0 for c in categories}
        if total_available > 0:
            # Base proportional allocation
            for c in categories:
                allocations[c] = int(round(remaining_slots * (available_counts[c] / total_available))) if available_counts[c] else 0

            # Ensure we don't allocate more than available
            for c in categories:
                allocations[c] = min(allocations[c], available_counts[c])

            # Adjust to hit remaining_slots exactly
            def allocated_total():
                return sum(allocations.values())

            # If under, add to categories with remaining inventory, highest scoring first
            if allocated_total() < remaining_slots:
                # Build a ranked list of candidates by next best score in each category
                while allocated_total() < remaining_slots:
                    best_cat = None
                    best_next = None
                    for c in categories:
                        if allocations[c] < available_counts[c]:
                            cand = category_groups[c][allocations[c]]
                            if best_next is None or tie_break_key(cand) < tie_break_key(best_next):
                                best_next = cand
                                best_cat = c
                    if best_cat is None:
                        break
                    allocations[best_cat] += 1

            # If over, remove from categories with the weakest marginal deal
            if allocated_total() > remaining_slots:
                while allocated_total() > remaining_slots:
                    worst_cat = None
                    worst_item = None
                    for c in categories:
                        if allocations[c] > 0:
                            item = category_groups[c][allocations[c] - 1]
                            if worst_item is None or tie_break_key(item) > tie_break_key(worst_item):
                                worst_item = item
                                worst_cat = c
                    if worst_cat is None:
                        break
                    allocations[worst_cat] -= 1

        added: List[DealDict] = []
        for c in categories:
            added.extend(category_groups[c][:allocations.get(c, 0)])

        # Backfill if still short
        if len(added) < remaining_slots:
            added_ids = set(d.get("deal_id") for d in added)
            for d in scored_deals:
                if len(added) >= remaining_slots:
                    break
                if d.get("deal_id") in added_ids:
                    continue
                added.append(d)

        top_deals.extend(added)
        top_deals.sort(key=tie_break_key)
        return top_deals[:top_n]

    def analyze_deals_debug(
        self,
        deals: List[DealDict],
        top_n: int = 6,
        balance_categories: Optional[bool] = None
    ) -> Tuple[List[DealDict], List[Tuple[DealDict, str]]]:
        """
        Debug variant that returns (top_deals, excluded_deals_with_reason).
        """
        excluded: List[Tuple[DealDict, str]] = []
        deals = self._dedupe_deals(deals)

        kept: List[DealDict] = []
        for d in deals:
            reason = self.get_exclusion_reason(d)
            if reason:
                excluded.append((d, reason))
            else:
                kept.append(d)

        top = self.analyze_deals(kept, top_n=top_n, balance_categories=balance_categories)
        return top, excluded

    # -------------------------
    # Output formatting
    # -------------------------
    def format_output(self, deals: List[DealDict], show_details: bool = True) -> str:
        if not deals:
            return "❌ No deals found matching criteria\n"

        retailer = deals[0].get("retailer", "Unknown")
        output = f"🏆 TOP {len(deals)} DEALS - {retailer}\n"
        output += f"{'=' * 60}\n\n"

        for i, deal in enumerate(deals, 1):
            trophy = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else ""
            priority_indicator = "⭐ " if deal.get("is_priority", False) else ""

            product = deal.get("product_name", "Unknown Product")
            price_display = (deal.get("price") or {}).get("display") or "Price N/A"
            score = int(deal.get("engagement_score", 0))
            category = deal.get("category", "N/A")

            output += f"{i}. {trophy}{priority_indicator}{product}\n"
            output += f"   💰 {price_display}"

            # Derived unit price (explainability)
            unit_price_display = deal.get("unit_price_display")
            if unit_price_display and unit_price_display not in (price_display or ""):
                output += f"  (≈ {unit_price_display})"

            details = []

            size_qty = deal.get("size_quantity")
            if size_qty and size_qty not in {"null", "None"}:
                details.append(f"Size: {size_qty}")

            unit = (deal.get("price") or {}).get("unit")
            if unit and str(unit) not in str(price_display):
                details.append(f"Unit: {unit}")

            fmt = deal.get("format") or deal.get("container_type")
            if fmt and fmt not in {"null", "None"}:
                details.append(f"Format: {fmt}")

            qty_required = deal.get("quantity_required")
            if qty_required and qty_required not in {"null", "None"}:
                details.append(f"Qty Required: {qty_required}")

            if details:
                output += f" | {' | '.join(details)}"

            output += "\n"

            if show_details:
                output += f"   📊 Score: {score} pts | 📂 {category}"
                if deal.get("is_priority", False):
                    output += " | ⭐ PRIORITY DEAL"
                output += "\n"

                viral = self.calculate_viral_pricing_score(deal)
                discount = self.calculate_discount_depth(deal)
                cat_weight = self.calculate_category_weight(deal)
                premium = self.calculate_premium_value(deal)
                social = self.calculate_social_appeal(deal)
                brand = self.calculate_brand_recognition(deal)
                priority_bonus = self.get_priority_bonus(deal)

                breakdown = (
                    f"   📈 Breakdown: Price={viral} | Discount={discount} | "
                    f"Category={cat_weight} | Premium={premium} | Social={social} | Brand={brand}"
                )
                if priority_bonus > 0:
                    breakdown += f" | Priority={priority_bonus}"
                output += breakdown + "\n"

            output += "\n"

        return output

    def analyze_retailer_comparison(self, all_deals: List[DealDict], retailers: List[str]) -> str:
        output = "🔄 MULTI-RETAILER COMPARISON\n"
        output += f"{'=' * 60}\n\n"

        for retailer in retailers:
            retailer_analyzer = DealAnalyzer(retailer_filter=retailer, config=self.config)
            retailer_deals = [d for d in all_deals if d.get("retailer") == retailer]
            top_deals = retailer_analyzer.analyze_deals(retailer_deals, top_n=3)

            if top_deals:
                output += f"📍 {retailer}\n"
                for i, deal in enumerate(top_deals, 1):
                    output += f"  {i}. {deal.get('product_name','')} - {(deal.get('price') or {}).get('display','')}\n"
                output += "\n"

        return output


def _cli():
    parser = argparse.ArgumentParser(description="Grocery Deal Analyzer (CLI)")
    parser.add_argument("--input", "-i", required=True, help="Path to deals JSON file")
    parser.add_argument("--top", "-n", type=int, default=6, help="Number of top deals to show")
    parser.add_argument("--retailer", "-r", default=None, help="Retailer filter (e.g., AMAZON_FRESH)")
    parser.add_argument("--no-details", action="store_true", help="Hide scoring details")
    parser.add_argument("--no-balance", action="store_true", help="Disable category balancing")
    parser.add_argument("--debug-excluded", action="store_true", help="Print excluded deals with reasons")

    args = parser.parse_args()

    with open(args.input, "r") as f:
        deals = json.load(f)

    analyzer = DealAnalyzer(retailer_filter=args.retailer)

    if args.debug_excluded:
        top, excluded = analyzer.analyze_deals_debug(deals, top_n=args.top, balance_categories=not args.no_balance)
        print(analyzer.format_output(top, show_details=not args.no_details))
        print("🧪 EXCLUDED DEALS (debug)\n" + "=" * 60)
        for d, reason in excluded[:200]:
            print(f"- {d.get('product_name','(unknown)')} [{d.get('retailer','')}] -> {reason}")
    else:
        top = analyzer.analyze_deals(deals, top_n=args.top, balance_categories=not args.no_balance)
        print(analyzer.format_output(top, show_details=not args.no_details))


if __name__ == "__main__":
    _cli()

# =========================
# HTML EMAIL GENERATION
# =========================

RETAILER_LOGOS = {
    "VONS": "https://upload.wikimedia.org/wikipedia/commons/0/0e/Vons_logo.svg",
    "RALPHS": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/96/Ralphs.svg/1024px-Ralphs.svg.png",
    "SMART_AND_FINAL": "https://play-lh.googleusercontent.com/fCa9uxi0baNL8iFHqLSWP8B3kti5OZL0sbDoCSZkQOg1e2OzRuKbkVjGlHlNl1j1h_0",
    "HEB": "https://upload.wikimedia.org/wikipedia/commons/3/35/HEB_logo.svg",
    "SPROUTS": "https://upload.wikimedia.org/wikipedia/commons/0/0d/Sprouts_Farmers_Market_logo.svg",
    "AMAZON_FRESH": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
    "WHOLE_FOODS": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Whole_Foods_Market_logo.svg",
}

DEFAULT_DEAL_IMAGE = "https://link.gelsons.com/custloads/760906850/md_1640571.jpg"


def _html_escape(s: Any) -> str:
    import html
    return html.escape(str(s) if s is not None else "")


def _format_save_line(deal: DealDict) -> str:
    price = deal.get("price") or {}
    savings_amount = price.get("savings_amount")
    savings_percent = price.get("savings_percent")
    if isinstance(savings_amount, (int, float)) and savings_amount > 0:
        return f"Save ${float(savings_amount):.2f}"
    if isinstance(savings_percent, (int, float)) and savings_percent > 0:
        return f"Save {int(round(float(savings_percent)))}%"
    # Multi-buy format as a "save"-style callout
    if (price.get("is_multibuy") or deal.get("multibuy_format")) and deal.get("multibuy_format"):
        return _html_escape(deal.get("multibuy_format"))
    return ""


def _format_regular_price(deal: DealDict) -> Optional[str]:
    price = deal.get("price") or {}
    orig = price.get("original_price")
    if isinstance(orig, (int, float)) and orig > 0:
        return f"${float(orig):.2f}"
    return None


def _format_sale_price(deal: DealDict) -> str:
    # Prefer display (already normalized for multibuy per-unit)
    disp = (deal.get("price") or {}).get("display")
    if disp:
        return _html_escape(disp)
    amt = (deal.get("price") or {}).get("amount")
    if isinstance(amt, (int, float)):
        return f"${float(amt):.2f}"
    return "Price N/A"


def _deal_size_text(deal: DealDict) -> str:
    sq = deal.get("size_quantity")
    if sq:
        return _html_escape(sq)
    # fallback to unit conversion, if present
    upd = deal.get("unit_price_display")
    if upd:
        return _html_escape(upd)
    return ""


def _render_deal_card(deal: DealDict) -> str:
    name = _html_escape(deal.get("product_name") or "Unknown")
    size_txt = _deal_size_text(deal)
    save_line = _format_save_line(deal)
    regular = _format_regular_price(deal)
    sale = _format_sale_price(deal)

    # Quantity required for multibuy
    qty_req = deal.get("quantity_required")
    if qty_req:
        # append to size line to keep layout stable
        if size_txt:
            size_txt = f"{size_txt} • Qty {int(qty_req)}"
        else:
            size_txt = f"Qty {int(qty_req)}"

    save_html = f'<p class="deal-save">{save_line}</p>' if save_line else '<p class="deal-save" style="color:#ffffff00; margin:0 0 6px 0;">&nbsp;</p>'
    regular_html = f'<span class="deal-regular">{regular}</span>' if regular else ""

    return f'''
      <div class="deal-card">
        <div class="deal-image-wrapper">
          <img src="{DEFAULT_DEAL_IMAGE}" alt="{name}" />
        </div>
        <p class="deal-name">{name}</p>
        <p class="deal-size">{size_txt}</p>
        {save_html}
        <p class="deal-prices">
          {regular_html}
          <span class="deal-sale">{sale}</span>
        </p>
      </div>
    '''


def _render_retailer_section(retailer: str, deals: List[DealDict], idx: int, total: int, top_n: int) -> str:
    logo = RETAILER_LOGOS.get(retailer) or RETAILER_LOGOS.get(retailer.upper()) or ""
    subtitle = f"Top {min(top_n, len(deals))} deals this week at {retailer.replace('_', ' ').title()}."

    # Build 2-up grid rows
    rows = []
    for r in range(0, len(deals), 2):
        left = _render_deal_card(deals[r])
        right = _render_deal_card(deals[r+1]) if r+1 < len(deals) else ""
        if right:
            row = f'''
              <tr>
                <td class="deal-column">{left}</td>
                <td class="deal-column">{right}</td>
              </tr>
            '''
        else:
            row = f'''
              <tr>
                <td class="deal-column">{left}</td>
                <td class="deal-column"></td>
              </tr>
            '''
        rows.append(row)

    rows_html = "\n".join(rows)

    logo_html = f'<img src="{logo}" alt="{_html_escape(retailer)} logo" class="retailer-logo" />' if logo else f'<span style="font-weight:800;">{_html_escape(retailer)}</span>'

    return f'''
      <div class="retailer-section">
        <div class="retailer-tag">Retailer {idx} of {total}</div>
        <h2 class="section-header">
          {logo_html}
        </h2>
        <p class="section-subtitle">{_html_escape(subtitle)}</p>

        <table class="deal-grid" role="presentation" cellpadding="0" cellspacing="0" border="0">
          {rows_html}
        </table>
      </div>
    '''


def _best_price_for_keywords(deals: List[DealDict], keywords: List[str]) -> Optional[float]:
    best = None
    for d in deals:
        name = (d.get("product_name") or "").lower()
        if not any(k in name for k in keywords):
            continue
        # Prefer comparable unit price if in lb
        up, up_unit, _ = DealAnalyzer().compute_unit_price(d)
        amt = None
        if up is not None and up_unit in {"lb", "fl oz"}:
            amt = float(up)
        else:
            p = (d.get("price") or {}).get("amount")
            if isinstance(p, (int, float)):
                amt = float(p)
        if amt is None:
            continue
        if best is None or amt < best:
            best = amt
    return best


def _render_compare_table(retailers: List[str], by_retailer_deals: Dict[str, List[DealDict]]) -> str:
    # Simple staple set; we only fill what we can find.
    staples = [
        ("Chicken (per lb)", ["chicken breast", "chicken thighs", "chicken thigh", "chicken"]),
        ("Beef (per lb)", ["ground beef", "steak", "sirloin", "ribeye", "beef"]),
        ("Apples", ["apple", "apples"]),
    ]

    header_cells = "".join([f'<th style="text-align:right;">{_html_escape(r.replace("_", " ").title())}</th>' for r in retailers])

    body_rows = []
    for label, kws in staples:
        cells = []
        for r in retailers:
            best = _best_price_for_keywords(by_retailer_deals.get(r, []), kws)
            if best is None:
                cells.append('<td class="price">—</td>')
            else:
                # If this looks like a per-lb staple, show /lb
                suffix = "/lb" if "per lb" in label.lower() or label.lower().startswith("chicken") or label.lower().startswith("beef") else ""
                cells.append(f'<td class="price">${best:.2f}{suffix}</td>')
        row = f"<tr><td>{_html_escape(label)}</td>{''.join(cells)}</tr>"
        body_rows.append(row)

    return f'''
      <table class="compare-table" role="presentation" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <th>Item</th>
          {header_cells}
        </tr>
        {''.join(body_rows)}
      </table>
    '''


def build_weekly_email_html(
    all_deals: List[DealDict],
    template_html: str,
    top_n_per_retailer: int,
    display_name: str = "there",
    email: str = "",
    zip_code: str = "",
    week_of: Optional[str] = None,
) -> str:
    """Generate a fully-filled HTML email using the provided template HTML."""
    # Determine week label
    if not week_of:
        week_of = datetime.date.today().strftime("%b %d")

    # Group deals by retailer and analyze each retailer separately
    retailers = sorted({(d.get("retailer") or "Unknown") for d in all_deals})
    by_retailer_raw: Dict[str, List[DealDict]] = {r: [d for d in all_deals if (d.get("retailer") or "Unknown") == r] for r in retailers}

    by_retailer_top: Dict[str, List[DealDict]] = {}
    for r in retailers:
        analyzer = DealAnalyzer(retailer_filter=r)
        by_retailer_top[r] = analyzer.analyze_deals(by_retailer_raw[r], top_n=top_n_per_retailer)

    # Chips: retailers list and deals count
    retailers_chip = " • ".join([r.replace("_", " ").title() for r in retailers])
    deals_picked = sum(len(v) for v in by_retailer_top.values())

    html_out = template_html

    # Replace top meta
    html_out = re.sub(r"Week of <strong>[^<]*</strong>", f"Week of <strong>{_html_escape(week_of)}</strong>", html_out)
    if zip_code:
        html_out = re.sub(r"ZIP <strong>[^<]*</strong>", f"ZIP <strong>{_html_escape(zip_code)}</strong>", html_out)

    # Replace greeting placeholders
    html_out = html_out.replace("${displayName}", _html_escape(display_name))
    html_out = html_out.replace("${encodeURIComponent(email)}", _html_escape(email))

    # Replace chips retailer list + deals count (best window left as static)
    html_out = re.sub(r"<p class=\"chip-body\">[^<]*</p>\s*</td>\s*<td class=\"chip\" width=\"25%\">\s*<p class=\"chip-title\">Deals picked</p>\s*<p class=\"chip-body\">[^<]*</p>",
                      f"<p class=\"chip-body\">{_html_escape(retailers_chip)}</p></td>\n                      <td class=\"chip\" width=\"25%\">\n                        <p class=\"chip-title\">Deals picked</p>\n                        <p class=\"chip-body\">{deals_picked} deals</p>",
                      html_out, flags=re.DOTALL)

    # Replace compare table
    compare_table_html = _render_compare_table(retailers, by_retailer_raw)
    html_out = re.sub(r"<table class=\"compare-table\b.*?</table>", compare_table_html, html_out, flags=re.DOTALL)

    # Replace retailer sections region (between divider and closing copy)
    sections_html = "\n".join([
        _render_retailer_section(r, by_retailer_top[r], idx=i+1, total=len(retailers), top_n=top_n_per_retailer)
        for i, r in enumerate(retailers)
    ])

    html_out = re.sub(r"<!-- ================= RETAILER 1:.*?-->\s*<div class=\"retailer-section\b.*?<!-- Closing copy -->",
                      sections_html + "\n\n                <!-- Closing copy -->",
                      html_out, flags=re.DOTALL)

    return html_out
