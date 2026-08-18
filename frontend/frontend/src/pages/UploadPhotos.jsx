import React, { useState } from "react";
import API from "../services/api";
import { authHeaders } from "../services/auth";

function UploadPhotos() {

    const [photos, setPhotos] = useState([]);

    const uploadPhotos = async () => {

        if (photos.length === 0) {

            alert("Select Event Photos");

            return;

        }

        const formData = new FormData();

        for (let i = 0; i < photos.length; i++) {

            formData.append("files", photos[i]);

        }

        try {

            const response = await API.post(

                "/upload-event",

                formData,

                {

                    headers: {

                        ...authHeaders(),

                        "Content-Type": "multipart/form-data"

                    }

                }

            );

            alert(response.data.message);

        }

        catch(err){

            console.log(err);

            alert("Upload Failed");

        }

    }

    return (
        <main className="content-shell">
            <section className="page-card">
                <div className="page-heading">
                    <div>
                        <p className="eyebrow">EVENT PHOTOS</p>
                        <h1>Upload event photos for matching</h1>
                        <p className="muted">Add all the event images you want scanned for face matches.</p>
                    </div>
                </div>
                <div className="upload-panel">
                    <input type="file" multiple onChange={(e) => setPhotos(e.target.files)} />
                    <button className="upload-button" onClick={uploadPhotos}>Upload</button>
                </div>
            </section>
        </main>
    );

}

export default UploadPhotos;
