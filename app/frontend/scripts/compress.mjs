// După `vite build`: variantele comprimate (.gz și .br) ale fișierelor din dist/assets.
// Serverul (WhiteNoise) le servește singur browserelor care le acceptă: interfața (~3 MB de JavaScript) ajunge
// de 3-4 ori mai repede prin rețea (Wi-Fi, VPN); pe fișierele cu amprentă în nume browserul le ține apoi un an.
import { readdirSync, statSync, readFileSync, writeFileSync } from 'node:fs'
import { join, dirname, extname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync, brotliCompressSync, constants } from 'node:zlib'

const assets = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist', 'assets')
const COMPRESSIBLE = new Set(['.js', '.mjs', '.css', '.svg', '.json', '.map', '.txt'])
let count = 0
let before = 0
let after = 0
for (const name of readdirSync(assets)) {
  const file = join(assets, name)
  if (!COMPRESSIBLE.has(extname(name)) || statSync(file).size < 1024) continue
  const data = readFileSync(file)
  const gz = gzipSync(data, { level: 9 })
  const br = brotliCompressSync(data, {
    params: { [constants.BROTLI_PARAM_QUALITY]: 11, [constants.BROTLI_PARAM_SIZE_HINT]: data.length },
  })
  writeFileSync(file + '.gz', gz)
  writeFileSync(file + '.br', br)
  count += 1
  before += data.length
  after += br.length
}
console.log(`compress: ${count} fișiere, ${(before / 1024 / 1024).toFixed(1)} MB → ${(after / 1024 / 1024).toFixed(1)} MB (brotli)`)
