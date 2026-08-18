import React, { useEffect, useRef, useState } from "react";
import API from "../services/api";
import { useNavigate } from "react-router-dom";
import { authHeaders } from "../services/auth";

export default function UploadSelfie() {
  const [selfie, setSelfie] = useState(null);
  const [preview, setPreview] = useState("");
  const [cameraOpen, setCameraOpen] = useState(false);
  const [error, setError] = useState("");
  const [searching, setSearching] = useState(false);
  const videoRef = useRef();
  const streamRef = useRef();
  const navigate = useNavigate();
  const stopCamera = () => { streamRef.current?.getTracks().forEach((track) => track.stop()); streamRef.current = null; setCameraOpen(false); };
  useEffect(() => {
    if (cameraOpen && videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
  }, [cameraOpen]);
  useEffect(() => () => { streamRef.current?.getTracks().forEach((track) => track.stop()); }, []);
  const chooseFile = (file) => { if (!file) return; setSelfie(file); setPreview(URL.createObjectURL(file)); setError(""); };
  const openCamera = async () => {
    if (!navigator.mediaDevices?.getUserMedia) { setError("This browser cannot access a camera. Open the app in Chrome or Edge on localhost, then try again."); return; }
    try { const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "user" } }, audio: false }); streamRef.current = stream; setError(""); setCameraOpen(true); }
    catch (err) {
      const messages = { NotAllowedError: "Camera permission was denied. Click the camera icon in your browser address bar, allow access, then try again.", NotFoundError: "No camera was found on this device.", NotReadableError: "Your camera is being used by another application. Close it and try again." };
      setError(messages[err.name] || "Camera could not start. Please check browser permissions and try again.");
    }
  };
  const capture = () => {
    const video = videoRef.current; const canvas = document.createElement("canvas");
    if (!video?.videoWidth) { setError("Camera is still starting. Wait one second and capture again."); return; }
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob((blob) => { if (blob) chooseFile(new File([blob], "camera-selfie.jpg", { type: "image/jpeg" })); }, "image/jpeg", 0.92);
    stopCamera();
  };
  const searchPhoto = async () => {
    if (!selfie) { setError("Choose or take a selfie first."); return; }
    const formData = new FormData(); formData.append("file", selfie); setSearching(true); setError("");
    try { const response = await API.post("/search", formData, { headers: authHeaders() }); navigate("/results", { state: { photos: response.data.matched_photos } }); }
    catch (err) { setError(err.response?.data?.message || "We could not search this selfie. Please try another clear image."); }
    finally { setSearching(false); }
  };
  return <main className="content-shell"><section className="page-card"><div className="page-heading"><div><p className="eyebrow">SELFIE MATCH</p><h1>Find your event photos</h1><p className="muted">Use a clear, front-facing selfie. Your camera image is only uploaded after you select Find My Photos.</p></div></div>
    <div className="selfie-options"><label className="selfie-option"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => chooseFile(e.target.files?.[0])} /><span className="option-icon">↥</span><strong>Upload a selfie</strong><small>Choose a photo from this device</small></label><button type="button" className="selfie-option" onClick={openCamera}><span className="option-icon">◉</span><strong>Take a selfie</strong><small>Use your device camera</small></button></div>
    {preview && <div className="selfie-preview"><img src={preview} alt="Selected selfie" /><div><strong>Selfie ready</strong><p>Use a well-lit image with one visible face.</p><button className="text-button" onClick={() => { setSelfie(null); setPreview(""); }}>Choose another</button></div></div>}
    {error && <p className="form-error">{error}</p>}
    <button className="primary-button selfie-submit" onClick={searchPhoto} disabled={searching}>{searching ? "Searching..." : "Find My Photos"}</button>
    {cameraOpen && <div className="modal" role="dialog" aria-modal="true" aria-label="Take a selfie"><div className="camera-modal"><button className="close-button" onClick={stopCamera} aria-label="Close camera">×</button><video ref={videoRef} autoPlay playsInline muted /><div className="camera-actions"><button className="secondary-button" onClick={stopCamera}>Cancel</button><button className="primary-button" onClick={capture}>Capture selfie</button></div></div></div>}
  </section></main>;
}
