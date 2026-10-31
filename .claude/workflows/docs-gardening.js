export const meta = {
  name: 'docs-gardening',
  description: 'Audit every document under docs/ for stale statements and broken cross-links; returns a JSON report',
  phases: ['List', 'Audit'],
}

phase('List')
const listing = await agent('List every Markdown file under docs/, recursively. Return only the paths.', {
  schema: {
    type: 'object',
    required: ['files'],
    properties: { files: { type: 'array', items: { type: 'string' } } },
  },
})

phase('Audit')
const audits = await pipeline(listing.files, file =>
  agent(
    `Read ${file}. Report (1) statements contradicted by the code or by a newer document, ` +
      `(2) relative links that do not resolve, (3) whether the file is listed neither in docs/llms.txt nor in the folder README.md that docs/llms.txt links (a .summary.md summary needs no line). Edit nothing.`,
    {
      label: file,
      schema: {
        type: 'object',
        required: ['file', 'stale', 'broken_links', 'missing_from_index'],
        properties: {
          file: { type: 'string' },
          stale: { type: 'array', items: { type: 'string' } },
          broken_links: { type: 'array', items: { type: 'string' } },
          missing_from_index: { type: 'boolean' },
        },
      },
    },
  ),
)

log(`audited ${audits.filter(Boolean).length} of ${listing.files.length} files`)
return audits.filter(Boolean)
