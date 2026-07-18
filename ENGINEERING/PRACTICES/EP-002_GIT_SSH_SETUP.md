###############################################################################
# Engineering Practice
###############################################################################

ID            : EP-002
Title         : Git SSH Setup
Status        : Approved
Version       : 1.0
Owner         : Engineering
Created       : 2026-07-18
Last Updated  : 2026-07-18

###############################################################################

# Git SSH Setup

**Status:** Approved Engineering Practice
**Date:** 2026-07-18

---

# Purpose

AI5R repositories use SSH authentication for all Git operations.

HTTPS authentication is not used because GitHub no longer supports password
authentication for Git operations.

---

# Why SSH

Benefits:

- no username prompt
- no password prompt
- no Personal Access Token required
- secure authentication
- suitable for long-term VPS development

---

# SSH Key

Location:

~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub

The SSH key belongs to the Linux user, not to a specific repository.

One SSH key may be reused across multiple AI5R repositories.

---

# Repository Configuration

Each repository stores its own remote configuration.

Example:

~/AI5R

~/AI5R-repo-hygiene

Both repositories may use:

git@github.com:alfikrraid-cmd/AI5R.git

Changing one repository's remote does not affect another repository.

---

# Configure Remote

Example:

git remote set-url origin git@github.com:alfikrraid-cmd/AI5R.git

Verify:

git remote -v

Expected:

origin  git@github.com:alfikrraid-cmd/AI5R.git (fetch)
origin  git@github.com:alfikrraid-cmd/AI5R.git (push)

---

# Verify Authentication

ssh -T git@github.com

Expected:

Hi alfikrraid-cmd! You've successfully authenticated.

---

# Daily Workflow

git pull

git add .

git commit

git push

No username or password should be requested.

---

# Engineering Rule

All AI5R development repositories should use SSH remotes.

Do not use HTTPS remotes unless there is a specific operational requirement.
