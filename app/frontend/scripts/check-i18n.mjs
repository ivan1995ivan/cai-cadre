// Verifică: fiecare cheie t('...') din cod există în RO și RU. Rulare: node scripts/check-i18n.mjs
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const ro = { ...(await import('../src/i18n/ro.ts')).default, ...(await import('../src/i18n/ro1.ts')).default, ...(await import('../src/i18n/ro2.ts')).default, ...(await import('../src/i18n/ro3.ts')).default, ...(await import('../src/i18n/ro4.ts')).default, ...(await import('../src/i18n/ro5.ts')).default, ...(await import('../src/i18n/ro6.ts')).default, ...(await import('../src/i18n/ro7.ts')).default, ...(await import('../src/i18n/ro8.ts')).default, ...(await import('../src/i18n/ro9.ts')).default }
const ru = { ...(await import('../src/i18n/ru.ts')).default, ...(await import('../src/i18n/ru1.ts')).default, ...(await import('../src/i18n/ru2.ts')).default, ...(await import('../src/i18n/ru3.ts')).default, ...(await import('../src/i18n/ru4.ts')).default, ...(await import('../src/i18n/ru5.ts')).default, ...(await import('../src/i18n/ru6.ts')).default, ...(await import('../src/i18n/ru7.ts')).default, ...(await import('../src/i18n/ru8.ts')).default, ...(await import('../src/i18n/ru9.ts')).default }

const files = []
const walk = (dir) => readdirSync(dir).forEach((f) => {
  const p = join(dir, f)
  if (statSync(p).isDirectory()) walk(p)
  else if (/\.tsx?$/.test(f)) files.push(p)
})
walk('src')

const get = (obj, key) => key.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj)
const missing = new Set()
for (const file of files) {
  const text = readFileSync(file, 'utf8')
  for (const m of text.matchAll(/\bt\(\s*['`]([a-zA-Z0-9_.]+)['`]/g)) {
    const key = m[1]
    if (key.endsWith('.')) continue
    for (const [lang, dict] of [['ro', ro], ['ru', ru]]) {
      if (typeof get(dict, key) !== 'string' && typeof get(dict, key) !== 'object') missing.add(`${lang}: ${key}  (${file})`)
    }
  }
}
console.log(missing.size ? [...missing].join('\n') : 'Toate cheile există.')
process.exit(missing.size ? 1 : 0)
