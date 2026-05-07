/* VIDEO */
const video=document.getElementById("hero-video");
if(Hls.isSupported()){
  const hls=new Hls();
  hls.loadSource("https://stream.mux.com/8wrHPCX2dC3msyYU9ObwqNdm00u3ViXvOSHUMRYSEe5Q.m3u8");
  hls.attachMedia(video);
}
/* SCROLL ANIMATION */
const reveals=document.querySelectorAll(".reveal");
window.addEventListener("scroll",()=>{
  reveals.forEach(el=>{
    if(el.getBoundingClientRect().top < window.innerHeight-100){
      el.classList.add("active");
    }
  });
});
/* CURSOR */
document.addEventListener('mousemove',e=>{
  cur.style.left=e.clientX+'px';
  cur.style.top=e.clientY+'px';
  cur2.style.left=e.clientX+'px';
  cur2.style.top=e.clientY+'px';
});
function toggleLoss(el){
    const item = el.parentElement;
  
    // Close others (optional but cleaner UX)
    document.querySelectorAll('.loss-item').forEach(i=>{
      if(i !== item) i.classList.remove('active');
    });
  
    // Toggle current
    item.classList.toggle('active');
  }
