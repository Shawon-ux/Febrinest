from django.db.models import Q

from .models import SIZES, Category

SORTS = {
    "new": ("Newest", "-created_at"),
    "low": ("Price: low to high", "price"),
    "high": ("Price: high to low", "-price"),
    "name": ("Name A–Z", "name"),
}


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def filter_products(request, qs, fixed_category=None):
    """Shared by the customer shop and the admin product list."""
    g = request.GET
    q = g.get("q", "").strip()
    category = fixed_category.slug if fixed_category else g.get("category", "")
    size = g.get("size", "")
    pmin, pmax = _int(g.get("min")), _int(g.get("max"))
    sort = g.get("sort", "new")
    only_stock = g.get("in_stock") == "1"

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category and not fixed_category:
        qs = qs.filter(category__slug=category)
    if size:
        qs = qs.filter(sizes__size=size, sizes__available=True)
    if pmin is not None:
        qs = qs.filter(price__gte=pmin)
    if pmax is not None:
        qs = qs.filter(price__lte=pmax)
    if only_stock:
        qs = qs.filter(sizes__available=True)
    qs = qs.distinct().order_by(SORTS.get(sort, SORTS["new"])[1], "-id")

    ctx = {
        "f": {"q": q, "category": category, "size": size, "min": g.get("min", ""),
              "max": g.get("max", ""), "sort": sort, "in_stock": only_stock},
        "filter_categories": Category.objects.all(),
        "filter_sizes": SIZES,
        "sorts": [(k, v[0]) for k, v in SORTS.items()],
        "filters_active": any([q, category and not fixed_category, size, pmin is not None,
                               pmax is not None, only_stock]),
    }
    return qs.select_related("category").prefetch_related("sizes"), ctx
