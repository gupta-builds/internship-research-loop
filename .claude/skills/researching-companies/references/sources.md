# Where to look, by kind of company

Read at step 3 of the workflow. The pages named are kinds of page, not guaranteed URLs: find the real URL with a search, then fetch it. Skip `indeed.com`, `glassdoor.com`, `simplify.jobs` and `linkedin.com/jobs/` for contacts; `enrich.py` excludes the same four (`_EXCLUDED_CONTACT_DOMAINS_RE`).

| Kind | Try first | Then | Usually missing |
|---|---|---|---|
| Startup | The posting's own page, the company site's careers and about pages, the engineering or product blog | The GitHub organization, a founder's post that the company site links | A recruiter name; a university program page |
| Large tech company | The university or early-career recruiting page, the posting's requisition page | The engineering blog, the newsroom | A named recruiter (the page lists a team inbox or a form) |
| Quant or trading firm | The campus or students page, the posting | Research or "insights" pages, a team page | Anything about the role beyond the posting; pay is rarely stated |
| Industrial or enterprise company | The careers portal posting (often a hosted applicant system), the early-career program page | The newsroom, the investor relations page for named products and programs | A blog; a GitHub organization; named people |

## Notes
- The applicant-system page for the posting is the company's own page even when it sits on a vendor domain, because the company publishes it. Cite it as the posting.
- A program-wide page and one requisition can carry different dates. Record each date next to the page it came from and let Anant choose which binds.
- A GitHub organization from `contact_signals.py` is a best search match. Confirm that the company's own site links to it before you treat it as theirs.
- A page that needs a login, a CAPTCHA or a cookie is skipped and written under Gaps.
