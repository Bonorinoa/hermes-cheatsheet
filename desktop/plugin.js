/**
 * Clickable title-bar mark that opens a cheatsheet.
 * Folder name must equal id. Plain ESM — jsx() calls, not JSX.
 * Reload: ⌘K → Reload desktop plugins.
 */

import {
  atom,
  Badge,
  CopyButton,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  EmptyState,
  haptic,
  host,
  PALETTE_AREA,
  SearchField,
  SegmentedControl,
  TITLEBAR_AREAS,
  Tip,
  useValue
} from '@hermes/plugin-sdk'
import { useEffect, useMemo, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'cheatsheet'
const $open = atom(false)
let pluginCtx = null

const HIDDEN_DESKTOP = new Set(['terminal', 'messaging', 'hidden'])

function profileParam() {
  const profile = host.state.profile && host.state.profile.get && host.state.profile.get()
  return profile ? { profile } : {}
}

function keepCommand(name, meta) {
  const desktop = meta && meta[name] && meta[name].desktop
  return !desktop || !HIDDEN_DESKTOP.has(desktop)
}

function commandGroups(catalog) {
  const meta = (catalog && catalog.commands) || {}
  const categories = Array.isArray(catalog && catalog.categories) ? catalog.categories : []
  const fromCategories = categories
    .map(category => ({
      name: category.name || 'Other',
      rows: (category.pairs || [])
        .filter(pair => pair && pair[0] && keepCommand(pair[0], meta))
        .map(pair => ({ name: pair[0], description: pair[1] || '' }))
    }))
    .filter(category => category.rows.length)

  if (fromCategories.length) {
    return fromCategories
  }

  const pairs = Array.isArray(catalog && catalog.pairs) ? catalog.pairs : []
  const rows = pairs
    .filter(pair => pair && pair[0] && keepCommand(pair[0], meta))
    .map(pair => ({ name: pair[0], description: pair[1] || '' }))

  return rows.length ? [{ name: 'Commands', rows }] : []
}

function sourceRank(source) {
  if (source === 'user' || source === 'git' || source === 'project') return 0
  if (source === 'pip') return 1
  if (source === 'bundled') return 3
  return 2
}

function pluginRows(payload) {
  const rows = payload && Array.isArray(payload.plugins) ? payload.plugins : []
  return rows
    .map(row => ({
      name: row.name || row.key || 'plugin',
      description: row.description || '',
      status: row.status || (row.enabled === false ? 'not enabled' : row.enabled ? 'enabled' : ''),
      source: row.source || '',
      version: row.version || ''
    }))
    .sort((a, b) => sourceRank(a.source) - sourceRank(b.source) || a.name.localeCompare(b.name))
}

function mcpRows(payload) {
  const rows = payload && Array.isArray(payload.servers) ? payload.servers : []
  return rows.map(row => ({
    name: row.name || 'server',
    description: [row.transport, row.source].filter(Boolean).join(' · '),
    status: row.enabled ? 'enabled' : 'not enabled',
    source: 'mcp',
    version: ''
  }))
}

function statusVariant(status) {
  const value = String(status || '').toLowerCase()
  if (value.includes('not') || value.includes('disable') || value.includes('fail') || value.includes('error')) {
    return value.includes('fail') || value.includes('error') ? 'destructive' : 'muted'
  }
  if (value.includes('enable')) return 'success'
  return 'outline'
}

function matches(query, ...parts) {
  const needle = query.trim().toLowerCase()
  if (!needle) return true
  return parts.join(' ').toLowerCase().includes(needle)
}

function Mark() {
  return jsx('svg', {
    'aria-hidden': true,
    className: 'size-3.5',
    fill: 'none',
    viewBox: '0 0 16 16',
    children: [
      jsx('rect', { height: '13', rx: '2.5', stroke: 'currentColor', width: '13', x: '1.5', y: '1.5' }, 'frame'),
      jsx('path', { d: 'M4.5 5.5h7M4.5 8h7M4.5 10.5h4.5', stroke: 'currentColor', strokeLinecap: 'round' }, 'lines')
    ]
  })
}

function CommandRow(row) {
  return jsxs('div', {
    className: 'flex items-start gap-2 border-b border-(--ui-stroke-tertiary) py-1.5 last:border-b-0',
    children: [
      jsx('code', {
        className: 'shrink-0 font-mono text-[0.75rem] text-(--ui-accent)',
        children: `/${row.name}`
      }),
      jsx('span', {
        className: 'min-w-0 flex-1 text-[0.75rem] leading-snug text-(--ui-text-secondary)',
        children: row.description || '—'
      }),
      jsx(CopyButton, {
        appearance: 'icon',
        buttonSize: 'icon-xs',
        label: `Copy /${row.name}`,
        text: `/${row.name}`
      })
    ]
  })
}

function PluginRow(row) {
  return jsxs('div', {
    className: 'flex items-start gap-2 border-b border-(--ui-stroke-tertiary) py-2 last:border-b-0',
    children: [
      jsxs('div', {
        className: 'min-w-0 flex-1',
        children: [
          jsxs('div', {
            className: 'flex flex-wrap items-center gap-1.5',
            children: [
              jsx('span', { className: 'text-[0.8125rem] font-medium', children: row.name }),
              row.status
                ? jsx(Badge, { size: 'xs', variant: statusVariant(row.status), children: row.status })
                : null,
              row.source
                ? jsx(Badge, { size: 'xs', variant: 'outline', children: row.source })
                : null
            ]
          }),
          row.description
            ? jsx('p', {
                className: 'mt-0.5 line-clamp-2 text-[0.75rem] leading-snug text-(--ui-text-secondary)',
                children: row.description
              })
            : null
        ]
      })
    ]
  })
}

function SectionLabel({ children }) {
  return jsx('div', {
    className: 'pb-1 pt-3 text-[0.65rem] font-medium uppercase tracking-[0.08em] text-(--ui-text-tertiary) first:pt-0',
    children
  })
}

function PassageRow({ hit, open, onToggle }) {
  const url = hit && hit.url
  const isHttps = typeof url === 'string' && url.startsWith('https://')
  const sourceLabel = isHttps
    ? (() => {
        const u = new URL(url)
        return u.host.replace(/^www\./, '') + u.pathname
      })()
    : ''
  return jsxs('div', {
    className: `border-l-2 py-2 pl-3 ${open ? 'border-(--ui-accent)' : 'border-transparent'}`,
    children: [
      jsx('button', {
        className: 'block w-full text-left',
        onClick: onToggle,
        type: 'button',
        children: jsxs('span', {
          className: 'flex items-baseline justify-between gap-4',
          children: [
            jsx('span', { className: 'text-[0.82rem] text-foreground', children: hit.title || 'Untitled' }),
            hit.where
              ? jsx('span', { className: 'shrink-0 text-[0.65rem] text-(--ui-text-tertiary)', children: hit.where })
              : null
          ]
        })
      }),
      jsx('p', {
        className: open
          ? 'mt-1 text-[0.75rem] leading-relaxed text-(--ui-text-secondary)'
          : 'mt-1 line-clamp-2 text-[0.75rem] leading-relaxed text-(--ui-text-secondary)',
        children: hit.text || ''
      }),
      open && isHttps
        ? jsx('button', {
            className: 'mt-1.5 text-[0.7rem] text-(--ui-accent) hover:underline',
            onClick: () => pluginCtx.os.openExternal(url),
            type: 'button',
            children: sourceLabel
          })
        : null
    ]
  })
}

function Sheet() {
  const [tab, setTab] = useState('commands')
  const [query, setQuery] = useState('')
  const [showBundled, setShowBundled] = useState(false)
  const [commands, setCommands] = useState(null)
  const [plugins, setPlugins] = useState(null)
  const [mcp, setMcp] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [facet, setFacet] = useState('all')
  const [openId, setOpenId] = useState('')
  const [rows, setRows] = useState(null)
  const [practicesError, setPracticesError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')
      try {
        const scope = profileParam()
        const catalog = await host.request('commands.catalog', scope)
        let pluginPayload
        try {
          pluginPayload = await host.request('plugins.manage', { action: 'list', ...scope })
        } catch {
          pluginPayload = await host.request('plugins.list', {})
        }
        let mcpPayload = null
        try {
          mcpPayload = await host.request('mcp.servers.list', scope)
        } catch {
          mcpPayload = null
        }
        if (cancelled) return
        setCommands(catalog)
        setPlugins(pluginPayload)
        setMcp(mcpPayload)
      } catch (err) {
        if (!cancelled) setError(err && err.message ? err.message : String(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  async function loadPractices(query, facet) {
    if (!pluginCtx) return
    const params = new URLSearchParams({ q: query, facet })
    setPracticesError('')
    setRows(null)
    try {
      const payload = await pluginCtx.rest(`/practices?${params.toString()}`)
      if (payload && Array.isArray(payload.hits)) {
        setRows(payload)
      } else {
        setPracticesError('The practices route returned an unexpected shape.')
        setRows([])
      }
    } catch {
      setPracticesError('Practices needs the backend')
      setRows([])
    }
  }

  useEffect(() => {
    if (tab !== 'practices') return
    const timer = setTimeout(() => {
      loadPractices(query, facet)
    }, 200)
    return () => clearTimeout(timer)
  }, [query, facet, tab])

  const groups = useMemo(() => commandGroups(commands), [commands])
  const agents = useMemo(() => pluginRows(plugins), [plugins])
  const servers = useMemo(() => mcpRows(mcp), [mcp])

  const visibleGroups = groups
    .map(group => ({
      ...group,
      rows: group.rows.filter(row => matches(query, row.name, row.description, group.name))
    }))
    .filter(group => group.rows.length)

  const bundledCount = agents.filter(row => row.source === 'bundled').length
  const visibleAgents = agents.filter(row => {
    if (!showBundled && row.source === 'bundled') return false
    return matches(query, row.name, row.description, row.status, row.source)
  })
  const visibleServers = servers.filter(row => matches(query, row.name, row.description, row.status))
  const commandCount = groups.reduce((sum, group) => sum + group.rows.length, 0)

  const facetOptions = [
    ['all', 'Docs & issues'],
    ['issue', 'Issues'],
    ['doc', 'Docs']
  ]

  const counts = rows && rows.counts ? rows.counts : null
  const gaps = rows && Array.isArray(rows.gaps) ? rows.gaps : []
  const prompts = rows && Array.isArray(rows.prompts) ? rows.prompts : []
  const hits = rows && Array.isArray(rows.hits) ? rows.hits : []

  return jsxs(DialogContent, {
    className: 'max-w-3xl',
    bodyClassName: 'max-h-[min(72vh,40rem)] gap-3',
    children: [
      jsxs(DialogHeader, {
        children: [
          jsx(DialogTitle, { children: 'Cheatsheet' }),
          jsx(DialogDescription, {
            children: 'Commands and plugins are live from this gateway. Practices retrieves cited passages — it does not invent advice.'
          })
        ]
      }),
      jsx(SearchField, {
        'aria-label': 'Filter the cheatsheet',
        onChange: setQuery,
        placeholder: tab === 'practices' ? 'A situation, not a chat' : 'Filter commands and plugins',
        value: query
      }),
      jsx(SegmentedControl, {
        onChange: setTab,
        options: [
          { id: 'commands', label: commandCount ? `Commands ${commandCount}` : 'Commands' },
          { id: 'plugins', label: 'Plugins' },
          { id: 'practices', label: 'Practices' }
        ],
        value: tab
      }),
      loading && tab !== 'practices'
        ? jsx('div', { className: 'py-8 text-center text-sm text-(--ui-text-tertiary)', children: 'Loading…' })
        : null,
      error && tab !== 'practices'
        ? jsx(EmptyState, { description: error, title: 'Could not read the gateway' })
        : null,
      !loading && !error && tab === 'commands'
        ? visibleGroups.length
          ? jsx('div', {
              children: visibleGroups.map(group =>
                jsxs('section', {
                  children: [
                    jsx(SectionLabel, { children: group.name }),
                    ...group.rows.map(row => jsx(CommandRow, row, row.name))
                  ]
                }, group.name)
              )
            })
          : jsx(EmptyState, {
              description: query ? 'Nothing matches that filter.' : 'The catalog came back empty.',
              title: 'No commands'
            })
        : null,
      !loading && !error && tab === 'plugins'
        ? jsxs('div', {
            children: [
              jsx('p', {
                className: 'text-[0.75rem] leading-relaxed text-(--ui-text-tertiary)',
                children:
                  'Agent plugins below are for the focused profile. This cheatsheet is a desktop plugin — those live in ~/.hermes/desktop-plugins and are not in this list.'
              }),
              bundledCount
                ? jsx('button', {
                    className: 'mt-2 text-[0.75rem] text-(--ui-accent) hover:underline',
                    onClick: () => setShowBundled(value => !value),
                    type: 'button',
                    children: showBundled ? 'Hide bundled' : `Show bundled (${bundledCount})`
                  })
                : null,
              visibleServers.length
                ? jsxs('section', {
                    children: [
                      jsx(SectionLabel, { children: 'MCP servers' }),
                      ...visibleServers.map(row => jsx(PluginRow, row, `mcp-${row.name}`))
                    ]
                  })
                : null,
              visibleAgents.length
                ? jsxs('section', {
                    children: [
                      jsx(SectionLabel, { children: 'Agent plugins' }),
                      ...visibleAgents.map(row => jsx(PluginRow, row, row.name))
                    ]
                  })
                : null,
              !visibleAgents.length && !visibleServers.length
                ? jsx(EmptyState, {
                    description: query
                      ? 'Nothing matches that filter.'
                      : 'No user plugins. Bundled ones are hidden until you show them.',
                    title: 'No plugins'
                  })
                : null
            ]
          })
        : null,
      tab === 'practices'
        ? jsxs('div', {
            children: [
              jsx('div', {
                className: 'flex gap-4',
                children: facetOptions.map(([value, label]) =>
                  jsx('button', {
                    className:
                      (facet === value ? 'text-(--ui-accent)' : 'text-(--ui-text-tertiary) hover:text-foreground') +
                      ' text-[0.75rem]',
                    onClick: () => setFacet(value),
                    type: 'button',
                    children: label
                  }, value)
                )
              }),
              rows === null && !practicesError
                ? jsx('div', { className: 'py-8 text-center text-sm text-(--ui-text-tertiary)', children: "Reading this install's docs…" })
                : null,
              practicesError && !rows.length
                ? jsx(EmptyState, {
                    title: 'Practices needs the backend',
                    description: 'Run hermes plugins enable cheatsheet, then enable Cheatsheet in Settings → Plugins, then ⌘K → Reload desktop plugins.'
                  })
                : null,
              rows && !practicesError
                ? jsxs('div', {
                    children: [
                      !hits.length && counts
                        ? jsx('p', {
                            className: 'text-[0.7rem] leading-relaxed text-(--ui-text-tertiary)',
                            children:
                              `${counts.doc} passages from this install. ${counts.issue} GitHub issues. ` +
                              gaps.join(' ')
                          })
                        : null,
                      !query && facet !== 'issue' && !hits.length
                        ? jsxs('div', {
                            children: [
                              jsx('div', {
                                className: 'text-[0.65rem] uppercase tracking-[0.08em] text-(--ui-text-tertiary)',
                                children: 'Try'
                              }),
                              ...prompts.map(prompt =>
                                jsx('button', {
                                  className: 'block py-1 text-left text-[0.8rem] text-(--ui-text-secondary) hover:text-foreground',
                                  onClick: () => setQuery(prompt),
                                  type: 'button',
                                  children: prompt
                                }, prompt)
                              )
                            ]
                          })
                        : null,
                      hits.length
                        ? jsx('div', {
                            children: hits.map(hit =>
                              jsx(PassageRow, {
                                hit,
                                open: openId === hit.id,
                                onToggle: () => setOpenId(openId === hit.id ? '' : hit.id)
                              }, hit.id)
                            )
                          })
                        : null,
                      query && !hits.length
                        ? jsx(EmptyState, {
                            title: 'Nothing retrieved',
                            description: 'No passage matches that situation.'
                          })
                        : null,
                      !query && facet === 'issue' && !hits.length
                        ? jsx('div', {
                            children: hits.slice(0, 12).map(hit =>
                              jsx(PassageRow, {
                                hit,
                                open: openId === hit.id,
                                onToggle: () => setOpenId(openId === hit.id ? '' : hit.id)
                              }, hit.id)
                            )
                          })
                        : null
                    ]
                  })
                : null
            ]
          })
        : null
    ]
  })
}

function CheatsheetButton() {
  const open = useValue($open)

  return jsxs('div', {
    className: 'contents',
    children: [
      jsx(Tip, {
        label: 'Cheatsheet',
        children: jsx('button', {
          'aria-label': 'Open cheatsheet',
          'aria-pressed': open,
          className:
            'inline-flex size-7 items-center justify-center rounded-[4px] text-(--ui-accent) [-webkit-app-region:no-drag] hover:bg-(--chrome-action-hover) hover:text-foreground',
          onClick: () => {
            haptic('tap')
            $open.set(!$open.get())
          },
          onPointerDown: event => event.stopPropagation(),
          type: 'button',
          children: jsx(Mark, {})
        })
      }),
      jsx(Dialog, {
        onOpenChange: $open.set,
        open,
        children: open ? jsx(Sheet, {}) : null
      })
    ]
  })
}

export default {
  id: ID,
  name: 'Cheatsheet',
  register(ctx) {
    pluginCtx = ctx
    ctx.register({
      id: 'favicon',
      area: TITLEBAR_AREAS.left,
      order: 20,
      render: () => jsx(CheatsheetButton, {})
    })

    ctx.register({
      id: 'open',
      area: PALETTE_AREA,
      data: {
        id: 'cheatsheet.open',
        keywords: ['slash', 'commands', 'plugins', 'practices', 'favicon', 'help'],
        label: 'Open cheatsheet',
        run: () => $open.set(true)
      }
    })
  }
}
