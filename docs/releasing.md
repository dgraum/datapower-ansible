# Publishing

Two checkouts stay separate.

The working repository holds every playbook, including laboratory inventories. Its history is not pushed to GitHub.

The public checkout is a second clone, by default `~/github/datapower-ansible`, with its own history. It tracks only [dgraum/datapower-ansible](https://github.com/dgraum/datapower-ansible). The branch `main` is the collection. The branch `master` on GitHub is the earlier incubator. Do not force-push `master`.

## Refresh the public clone

From the working repository:

```bash
python3 scripts/stage_public.py
```

The script copies the collection core and the example directories named in `PUBLIC_EXAMPLES`. It refuses the copy when a laboratory name or address is present. Commit and push from the public clone, not from the working tree.

## Add an example later

Prove the playbook in the working repository. When it is ready, add its directory name to `PUBLIC_EXAMPLES` in `scripts/stage_public.py`, run the script, then review the diff in the public clone and push that commit. The collection version and the example ship in the same tag.

## First publication of main

```bash
cd ~/github/datapower-ansible
git init -b main
git add .
git commit -m "Release gr.idg 1.0.0."
git remote add origin https://github.com/dgraum/datapower-ansible.git
git push -u origin main
git tag v1.0.0
git push origin v1.0.0
```

`v1.0.0` must match `version` in `galaxy.yml`. `main` is the default branch. `master` stays available for the incubator.

The release workflow builds `gr-idg-1.0.0.tar.gz` and attaches it to the GitHub release. It publishes to Galaxy when the repository secret `GALAXY_API_KEY` is set.

## Galaxy

1. Create the namespace `gr` at [galaxy.ansible.com](https://galaxy.ansible.com/) with the GitHub account that owns this repository.
2. Store the Galaxy API token as the repository secret `GALAXY_API_KEY`.
3. Push the tag. Until that namespace exists, install the Git tag shown in the README. The collection name remains `gr.idg`.
