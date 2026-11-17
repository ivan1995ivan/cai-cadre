from . import output, registry


def sample(request, lang, options):
    """Previzualizarea șablonului „report” în editorul formelor de tipar: structura personalului de azi."""
    p = registry.Params(user=request.user, lang=lang)
    p.on_date = p.today
    p.date_from, p.date_to = p.today.replace(day=1), p.today
    p.year, p.month = p.today.year, p.today.month
    return output.print_context(registry.run("structure", p))
