// Initialize the rotating globe
const globeContainer = document.getElementById("globe-container");

const Globe = window.Globe;
const globe = Globe()(globeContainer)
  .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")
  .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png");

// Zoom and auto-rotate
globe.controls().autoRotate = true;
globe.controls().autoRotateSpeed = 0.8;
globe.controls().enableZoom = true;

// Smooth scroll function
function scrollToSection(id) {
  document.getElementById(id).scrollIntoView({ behavior: "smooth" });
}
