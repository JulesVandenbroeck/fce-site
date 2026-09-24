# Teacher CLI

Two commands, run from the server machine, in the project's virtualenv.

## Create a class

```
python -m fce_web.store create-class
```

Prints a new class code (e.g. `A3F7QK`). Give it to your students; they type it into the
join screen along with a nickname (not their real name).

## Purge a class

```
python -m fce_web.store purge <code>
```

Deletes the class and **every** student and mission-completion row under it. Prints how
many rows were removed. Unknown code -> non-zero exit and an error message, nothing
deleted.

**This is permanent.** There is no undo and no backup taken first. Only students'
nicknames and mission progress are stored (no real names, no IP addresses) but once
purged, that class's data is gone.
