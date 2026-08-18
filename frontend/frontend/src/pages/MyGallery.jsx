import React, { useEffect, useRef, useState } from "react";
import API from "../services/api";
import { authHeaders, session } from "../services/auth";

export default function MyGallery() {
  const [photos, setPhotos] = useState([]);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef();

  const load = async () => {
    try { setLoading(true); setPhotos((await API.get("/gallery", { headers: authHeaders() })).data.photos); }
    catch (err) { setMessage(err.response?.data?.detail || "Could not load your gallery."); }
    finally { setLoading(false); }
  };
  useEffect(() => { if (session()) load(); }, []);

  const upload = async (event) => {
    const files = event.target.files;
    if (!files?.length) return;
    const data = new FormData();
    [...files].forEach((file) => data.append("files", file));
    setUploading(true); setMessage("");
    try { const result = await API.post("/gallery/upload", data, { headers: authHeaders() }); setMessage(result.data.message); inputRef.current.value = ""; await load(); }
    catch (err) { setMessage(err.response?.data?.detail || "Upload failed. Please try again."); }
    finally { setUploading(false); }
  };
  const remove = async (photo) => {
    if (!window.confirm(`Delete “${photo.title}”? This cannot be undone.`)) return;
    try { await API.delete(`/gallery/${photo.id}`, { headers: authHeaders() }); setPhotos((items) => items.filter((item) => item.id !== photo.id)); setSelected(null); setMessage("Photo deleted."); }
    catch (err) { setMessage(err.response?.data?.detail || "Could not delete this photo."); }
  };

  if (!session()) return <main className="empty-state"><h1>Please sign in</h1><p>Sign in to upload and view your personal gallery.</p></main>;
  return <main className="content-shell gallery-page">
    <header className="page-heading"><div><p className="eyebrow">YOUR PHOTOS</p><h1>My gallery</h1><p className="muted">A private place for the moments you want to keep.</p></div>
      <label className={`upload-button ${uploading ? "disabled" : ""}`}><input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp,image/gif" multiple onChange={upload} disabled={uploading} />{uploading ? "Uploading..." : "Upload photos"}</label>
    </header>
    {message && <p className="status-message">{message}</p>}
    {loading ? <p className="loading">Loading your photos...</p> : photos.length === 0 ? <section className="empty-gallery"><div>▧</div><h2>Your gallery is empty</h2><p>Upload one or more photos to build your private collection.</p><button className="primary-button" onClick={() => inputRef.current?.click()}>Choose photos</button></section> :
      <div className="gallery-grid">{photos.map((photo) => <button className="gallery-item" key={photo.id} onClick={() => setSelected(photo)}><img src={photo.thumbnail_url} alt={photo.title} /><span>{photo.title}</span></button>)}</div>}
    {selected && <div className="modal" role="dialog" aria-modal="true" aria-label={selected.title} onClick={() => setSelected(null)}><div className="photo-modal" onClick={(event) => event.stopPropagation()}><button className="close-button" onClick={() => setSelected(null)} aria-label="Close photo">×</button><img src={selected.image_url} alt={selected.title} /><div className="photo-modal-footer"><h2>{selected.title}</h2><button className="danger-button" onClick={() => remove(selected)}>Delete photo</button></div></div></div>}
  </main>;
}
