# Git, in plain language

If branches and PRs feel fuzzy, read this once. Five minutes, and you'll be
unblocked for the whole hackathon.

## The mental model

Think of `main` as the **clean demo copy** — the version we'd show a judge
right now. Nobody edits it directly.

A **branch** is your own copy of the project to mess around in. Breaking
things on your branch cannot break anyone else's work or the demo.

A **pull request (PR)** is you saying "my branch is ready — please fold it
into the clean copy." Someone glances at it, clicks merge, and now your work
is part of `main`.

That's the whole thing. Branch → work → PR → merge.

## First time only

```bash
git clone https://github.com/eliseoa-dev/priceoutcollective.git
cd priceoutcollective
```

## Every time you start a piece of work

```bash
git checkout main          # go to the clean copy
git pull                   # get everyone else's latest work
git checkout -b yourname/what-youre-doing
```

That last command makes your branch *and* switches you onto it. Name it
after yourself so nobody wonders whose it is — `maya/voucher-scenario`,
`sam/map-colors`.

## While you work

Save your progress as often as you like:

```bash
git add .
git commit -m "short note about what changed"
```

Commit early and often. A commit is a save point you can always come back to.

## When you're ready to share it

```bash
git push -u origin yourname/what-youre-doing
```

GitHub prints a link. Click it, write a sentence about what you did, hit
**Create pull request**. Done — tell the team in chat.

## The three things that actually go wrong

**"I committed to `main` by accident."**
Not a crisis. Nothing is lost:
```bash
git branch yourname/my-work    # bookmark your commits on a new branch
git reset --hard origin/main   # put main back how it was
git checkout yourname/my-work  # continue on your branch
```

**"It says my branch has conflicts."**
Two people edited the same lines. Pull `main` into your branch and Git will
mark the clashing spots in the file with `<<<<<<<` markers — delete the
markers, keep the version that's right, commit:
```bash
git pull origin main
```
If it looks scary, grab whoever wrote the other half. Two minutes together
beats twenty minutes alone.

**"I'm scared I'll delete someone's work."**
You basically can't, as long as you never run `git push --force`. Don't run
that. Everything else is recoverable.

## The one rule

**Never `git push --force`.** It's the only common command that can actually
destroy a teammate's work. Everything else, we can undo.

## Staying out of each other's way

Our folders are deliberately separate — `map/`, `policy_calculator/`,
`data/`. If you only touch your own folder, you will essentially never hit a
conflict. The one shared file is `data/zips.csv`; if you need to change its
columns, say so in chat first, because both other pieces read it.
