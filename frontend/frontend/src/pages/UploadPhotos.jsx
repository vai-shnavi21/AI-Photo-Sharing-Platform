import React, { useState } from "react";
import API from "../services/api";

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

        <div style={{textAlign:"center"}}>

            <h2>Upload Event Photos</h2>

            <input

                type="file"

                multiple

                onChange={(e)=>setPhotos(e.target.files)}

            />

            <br/><br/>

            <button

                onClick={uploadPhotos}

            >

                Upload

            </button>

        </div>

    );

}

export default UploadPhotos;