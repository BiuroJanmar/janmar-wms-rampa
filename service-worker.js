self.addEventListener('fetch', function(event) {
  // Zapewnia stabilne przesyłanie zdjęć palet i wag Janmar w tle
  event.respondWith(fetch(event.request));
});
