# Starting the server

```
python -m fce_web
```

Binds `0.0.0.0:8000` by default, so students on the same classroom network reach it at
`http://<your machine's LAN IP>:8000` (find that IP with your OS's usual network settings
panel). Pass `--host 127.0.0.1` to refuse LAN connections and keep it to one laptop, or
`--port <n>` to use a different port. This launch turns uvicorn's access log off, so no
student's IP address is ever printed or logged (`docs/design-brief.md` §6) -- the documented
alternative, `uvicorn --factory fce_web.app:create_app`, does not do that and should not be
used for a classroom.

All student data (class codes, nicknames, mission progress) lives in one SQLite file under
`FCE_HOME` (default `~/.fce`, override with the `FCE_HOME` environment variable).

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
