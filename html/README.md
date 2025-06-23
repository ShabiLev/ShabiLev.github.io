# Personal Résumé Site Template

This repository is a ready‑to‑fork template for a single‑page résumé website hosted on **GitHub Pages**.

## Quick start

1. **Clone / fork** this repo into a repository named `<username>.github.io`.  
   (If you already have that repo, just copy these files into it.)
2. Push to `main` – GitHub Pages will automatically publish the site at  
   `https://<username>.github.io/`.
3. Replace the placeholders in:

   * `index.html` – name, role, bio, experience, skills, contact details
   * `assets/css/style.css` – color overrides if desired
   * `assets/js/main.js` – custom JavaScript if needed
   * `resume.pdf` – your actual résumé file

4. Insert your **Google Analytics** measurement ID in `index.html` (`{{GA_MEASUREMENT_ID}}`).

## Folder structure

```
.
├─ index.html
├─ resume.pdf            # replace with your real PDF
├─ assets/
│  ├─ css/style.css
│  ├─ js/main.js
│  └─ img/               # keep images here
└─ .nojekyll
```

## Custom domain (optional)

1. Buy a domain and create a CNAME record pointing to `<username>.github.io`.
2. In the repo **Settings ➔ Pages** add your domain in **Custom domain**.

Enjoy your new site! 🎉
