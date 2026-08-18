import React from "react";
import { API_BASE_URL } from "../services/api";

function PhotoCard({ photo }) {
    const src = photo.photo.startsWith("http") ? photo.photo : `${API_BASE_URL}/uploads/event_photos/${photo.photo}`;
    const filename = photo.photo.split("/").pop().split("?")[0] || "event-photo";

    const downloadImage = async () => {
        try {
            const response = await fetch(src);
            if (!response.ok) {
                throw new Error(`Failed to download image: ${response.statusText}`);
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error(err);
            alert("Unable to download image. Please try again.");
        }
    };

    return (
        <article className="photo-card">
            <div className="photo-preview">
                <img src={src} alt={filename} />
            </div>
            <div className="photo-details">
                <h4>{filename}</h4>
                <p>Similarity: <strong>{photo.similarity}</strong></p>
            </div>
            <button className="download-button" onClick={downloadImage}>Download</button>
        </article>
    );
}

export default PhotoCard;
