import React,{useState} from "react";
import API from "../services/api";
import {useNavigate} from "react-router-dom";

function UploadSelfie(){

    const [selfie,setSelfie]=useState(null);

    const navigate=useNavigate();

    const searchPhoto=async()=>{

        if(!selfie){

            alert("Select Selfie");

            return;

        }

        const formData=new FormData();

        formData.append("file",selfie);

        try{

            const response=await API.post(

                "/search",

                formData,

                {

                    headers:{

                        "Content-Type":"multipart/form-data"

                    }

                }

            );

            navigate(

                "/results",

                {

                    state:{

                        photos:response.data.matched_photos

                    }

                }

            );

        }

        catch(err){

            console.log(err);

        }

    }

    return(

        <div style={{textAlign:"center"}}>

            <h2>Upload Selfie</h2>

            <input

                type="file"

                onChange={(e)=>setSelfie(e.target.files[0])}

            />

            <br/><br/>

            <button

                onClick={searchPhoto}

            >

                Find My Photos

            </button>

        </div>

    );

}

export default UploadSelfie;