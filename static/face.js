const M='/static/models';
async function loadModels(){await faceapi.nets.tinyFaceDetector.loadFromUri(M);await faceapi.nets.faceLandmark68Net.loadFromUri(M);await faceapi.nets.faceRecognitionNet.loadFromUri(M);}
async function cam(v){v.srcObject=await navigator.mediaDevices.getUserMedia({video:true});await v.play();}
async function desc(v){const r=await faceapi.detectSingleFace(v,new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceDescriptor();return r?Array.from(r.descriptor):null;}
async function post(u,d){return (await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({d})})).json();}
async function initCam(v,st){st.textContent='Memuat model wajah...';await loadModels();await cam(v);st.textContent='Kamera siap';}
