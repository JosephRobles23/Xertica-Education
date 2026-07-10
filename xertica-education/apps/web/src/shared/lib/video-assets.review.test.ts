import { primaryVideoPreviewMode, renderedVideoUrlFromAsset } from './video-assets'

if (primaryVideoPreviewMode({ renderedVideoUrl: 'https://cdn.example.com/final.mp4', hasYoutubeRecommendation: true }) !== 'ai') {
  throw new Error('Si ya existe un video renderizado, el preview principal debe mostrar el asset AI antes que YouTube.')
}

if (primaryVideoPreviewMode({ renderedVideoUrl: '', hasYoutubeRecommendation: true }) !== 'youtube') {
  throw new Error('Sin video renderizado, el preview principal debe seguir mostrando el candidato de YouTube.')
}

if (renderedVideoUrlFromAsset({ storage_path: 'https://cdn.example.com/storage.mp4', video_url: 'https://cdn.example.com/result.mp4' }) !== 'https://cdn.example.com/storage.mp4') {
  throw new Error('El storage_path persistido debe prevalecer como fuente de verdad del video renderizado.')
}

if (renderedVideoUrlFromAsset({ video_url: 'https://cdn.example.com/result.mp4' }) !== 'https://cdn.example.com/result.mp4') {
  throw new Error('Si el backend aún solo devuelve video_url, el helper debe seguir resolviéndolo.')
}
