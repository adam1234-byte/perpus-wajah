const M='/static/models';
let ready=false;
async function loadModels(){
  if(ready)return;
  await faceapi.nets.tinyFaceDetector.loadFromUri(M);
  await faceapi.nets.faceLandmark68Net.loadFromUri(M);
  await faceapi.nets.faceRecognitionNet.loadFromUri(M);
  ready=true;
}
function opt(){return new faceapi.TinyFaceDetectorOptions({inputSize:320,scoreThreshold:0.5});}
async function startCam(v){
  v.srcObject=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480,facingMode:'user'},audio:false});
  await v.play();
}
function camError(e){
  const n=e&&e.name?e.name:String(e);
  if(n==='NotAllowedError')return 'Izin kamera ditolak. Klik ikon kunci di address bar, izinkan Kamera, lalu refresh.';
  if(n==='NotFoundError')return 'Kamera tidak ditemukan.';
  if(n==='NotReadableError')return 'Kamera dipakai aplikasi lain (Zoom/Meet). Tutup lalu refresh.';
  return 'Kamera gagal: '+n+' '+(e&&e.message?e.message:'');
}
function liveDetect(v,c,st,onFace){
  const ctx=c.getContext('2d');
  async function loop(){
    try{
      if(v.videoWidth){
        c.width=v.videoWidth;c.height=v.videoHeight;
        const r=await faceapi.detectSingleFace(v,opt());
        ctx.clearRect(0,0,c.width,c.height);
        if(r){
          const b=r.box;
          ctx.lineWidth=4;ctx.strokeStyle='#16a34a';ctx.strokeRect(b.x,b.y,b.width,b.height);
          st.textContent='Wajah terdeteksi';st.className='st ok';
          if(onFace)onFace(r);
        }else{
          st.textContent='Wajah tidak terdeteksi. Hadap kamera dan cari cahaya.';st.className='st bad';
        }
      }
    }catch(e){}
    setTimeout(loop,250);
  }
  loop();
}
async function desc(v,n){
  n=n||1;const all=[];
  for(let i=0;i<n;i++){
    const r=await faceapi.detectSingleFace(v,opt()).withFaceLandmarks().withFaceDescriptor();
    if(!r)return null;
    all.push(Array.from(r.descriptor));
    if(i<n-1)await new Promise(s=>setTimeout(s,300));
  }
  return all[0].map((_,j)=>all.reduce((a,d)=>a+d[j],0)/all.length);
}
async function post(u,d){
  return (await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({d})})).json();
}
async function initCam(v,c,st,onFace){
  st.textContent='Memuat model wajah...';
  await loadModels();
  await startCam(v);
  liveDetect(v,c,st,onFace);
}
