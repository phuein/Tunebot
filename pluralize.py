# Return the word with an added "s" if n != 1.
# Optional set plural form.
def pluralize(s="", n=0, pluralForm=None):
    if n != 1:
        if pluralForm is None:
            s += "s"
        else:
            s = pluralForm
    
    return s