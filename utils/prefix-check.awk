BEGINFILE { mod = "" }
/^module / { mod = $2; }
mod && /^ *prefix / {
    pfx = gensub(/['";]/, "", "g", $2);
    if (pfx in prefixes) {
        printf("duplicate prefixes: %s for modules" \
               " %s and %s\n",
               pfx, prefixes[pfx], mod);
    } else {
        prefixes[pfx] = mod;
    }
    nextfile;
}
