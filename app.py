from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify
import os
from moviepy.editor import VideoFileClip, AudioFileClip
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')

# Create necessary folders
UPLOAD_FOLDER = "uploads"
AUDIO_FOLDER = "audio"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(os.path.join('static', 'processed'), exist_ok=True)

# Dictionary to store session data
sessions = {}

@app.route('/')
def index():
    return render_template('index.html', company_name="Mutex")

@app.route('/extract', methods=['POST'])
def extract_audio():
    logger.debug("Extract audio endpoint called")
    
    if 'video' not in request.files:
        logger.error("No file in request")
        return jsonify({"status": "error", "message": "No file uploaded"})
    
    file = request.files['video']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({"status": "error", "message": "No selected file"})
    
    try:
        # Generate unique ID for this extraction
        session_id = str(uuid.uuid4())
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{session_id}{file_extension}"
        
        logger.debug(f"Processing file: {original_filename}")
        
        video_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(video_path)
        logger.debug(f"Saved video to {video_path}")
        
        audio_filename = f"{session_id}.wav"
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        
        # Extract audio with exact duration
        logger.debug("Starting audio extraction")
        video_clip = VideoFileClip(video_path)
        
        if not video_clip:
            logger.error("Failed to load video file")
            return jsonify({"status": "error", "message": "Failed to load video file"})
            
        audio_clip = video_clip.audio
        
        if audio_clip is None:
            logger.error("No audio track found in video")
            video_clip.close()
            return jsonify({"status": "error", "message": "No audio track found in video"})
            
        logger.debug("Writing audio file")
        audio_clip.write_audiofile(audio_path, codec='pcm_s16le')
        audio_clip.close()
        video_clip.close()
        logger.debug(f"Audio extracted to {audio_path}")
        
        # Store the session info
        sessions[session_id] = {
            "type": "extract",
            "original_filename": original_filename,
            "audio_filename": audio_filename,
            "audio_path": audio_path
        }
        
        logger.debug(f"Session created with ID: {session_id}")
        return jsonify({
            "status": "success", 
            "message": "Audio extracted successfully!",
            "session_id": session_id,
            "original_filename": original_filename
        })
    except Exception as e:
        logger.exception(f"Error during extraction: {str(e)}")
        return jsonify({"status": "error", "message": f"Error during extraction: {str(e)}"})

@app.route('/download/<session_id>')
def download_audio(session_id):
    logger.debug(f"Download requested for session: {session_id}")
    
    if session_id not in sessions:
        logger.error(f"Session not found: {session_id}")
        return "Session not found", 404
    
    session_data = sessions[session_id]
    try:
        if session_data["type"] == "extract":
            if not os.path.exists(session_data["audio_path"]):
                logger.error(f"Audio file not found: {session_data['audio_path']}")
                return "Audio file not found", 404
                
            logger.debug(f"Sending audio file: {session_data['audio_path']}")
            return send_file(session_data["audio_path"], 
                            as_attachment=True, 
                            download_name=os.path.splitext(session_data["original_filename"])[0] + ".wav")
        else:
            # For replaced audio video
            if not os.path.exists(session_data["output_path"]):
                logger.error(f"Video file not found: {session_data['output_path']}")
                return "Video file not found", 404
                
            logger.debug(f"Sending video file: {session_data['output_path']}")
            return send_file(session_data["output_path"], 
                            as_attachment=True, 
                            download_name="mutex_" + session_data["original_filename"])
    except Exception as e:
        logger.exception(f"Error during download: {str(e)}")
        return f"Error processing download: {str(e)}", 500

# Routes for audio replacement functionality
@app.route('/upload_video', methods=['POST'])
def upload_video():
    logger.debug("Upload video endpoint called")
    
    if 'video' not in request.files:
        logger.error("No video in request")
        return jsonify({"status": "error", "message": "No video uploaded"})
    
    file = request.files['video']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({"status": "error", "message": "No selected file"})
    
    try:
        # Generate unique ID for this session
        session_id = str(uuid.uuid4())
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{session_id}{file_extension}"
        
        video_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(video_path)
        logger.debug(f"Saved video to {video_path}")
        
        # Store the session info
        sessions[session_id] = {
            "type": "replace",
            "original_filename": original_filename,
            "video_path": video_path,
            "stage": "video_uploaded"
        }
        
        logger.debug(f"Session created with ID: {session_id}")
        return jsonify({
            "status": "success", 
            "message": "Video uploaded successfully!",
            "session_id": session_id,
            "original_filename": original_filename
        })
    except Exception as e:
        logger.exception(f"Error during video upload: {str(e)}")
        return jsonify({"status": "error", "message": f"Error during upload: {str(e)}"})

@app.route('/upload_audio/<session_id>', methods=['POST'])
def upload_audio(session_id):
    logger.debug(f"Upload audio endpoint called for session: {session_id}")
    
    if session_id not in sessions:
        logger.error(f"Session not found: {session_id}")
        return jsonify({"status": "error", "message": "Session not found"})
    
    if sessions[session_id]["type"] != "replace" or sessions[session_id]["stage"] != "video_uploaded":
        logger.error(f"Invalid session state: {sessions[session_id]['stage']}")
        return jsonify({"status": "error", "message": "Invalid session state"})
    
    if 'audio' not in request.files:
        logger.error("No audio in request")
        return jsonify({"status": "error", "message": "No audio uploaded"})
    
    file = request.files['audio']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({"status": "error", "message": "No selected file"})
    
    try:
        audio_path = os.path.join(UPLOAD_FOLDER, f"audio_{session_id}{os.path.splitext(file.filename)[1]}")
        file.save(audio_path)
        logger.debug(f"Saved audio to {audio_path}")
        
        # Update session with audio info
        sessions[session_id]["audio_path"] = audio_path
        sessions[session_id]["audio_filename"] = file.filename
        sessions[session_id]["stage"] = "audio_uploaded"
        
        # Process the video
        logger.debug("Starting video processing")
        video_path = sessions[session_id]["video_path"]
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return jsonify({"status": "error", "message": "Video file not found"})
            
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return jsonify({"status": "error", "message": "Audio file not found"})
        
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        
        # If audio is longer than video, trim it
        if audio.duration > video.duration:
            logger.debug(f"Trimming audio from {audio.duration}s to {video.duration}s")
            audio = audio.subclip(0, video.duration)
        
        # If audio is shorter than video, we keep it as is (the video will be silent after the audio ends)
        video = video.set_audio(audio)
        
        output_filename = f"output_{session_id}.mp4"
        static_output_path = os.path.join('static', 'processed', output_filename)
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        
        logger.debug(f"Writing video to {output_path}")
        video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        # Also save to static folder for preview
        logger.debug(f"Writing preview video to {static_output_path}")
        video.write_videofile(static_output_path, codec="libx264", audio_codec="aac")
        
        # Close clips to free resources
        audio.close()
        video.close()
        
        # Update session with output info
        sessions[session_id]["output_path"] = output_path
        sessions[session_id]["static_output_path"] = static_output_path
        sessions[session_id]["output_filename"] = output_filename
        sessions[session_id]["stage"] = "completed"
        
        logger.debug(f"Processing completed for session: {session_id}")
        return jsonify({
            "status": "success", 
            "message": "Video processed successfully!",
            "session_id": session_id,
            "output_filename": output_filename
        })
    except Exception as e:
        logger.exception(f"Error during processing: {str(e)}")
        sessions[session_id]["stage"] = "error"
        sessions[session_id]["error"] = str(e)
        return jsonify({"status": "error", "message": f"Error during processing: {str(e)}"})

@app.route('/get_status/<session_id>')
def get_status(session_id):
    logger.debug(f"Status requested for session: {session_id}")
    
    if session_id not in sessions:
        logger.error(f"Session not found: {session_id}")
        return jsonify({"status": "error", "message": "Session not found"})
    
    logger.debug(f"Returning status for session: {session_id}")
    return jsonify({
        "status": "success",
        "session_data": {
            "type": sessions[session_id]["type"],
            "stage": sessions[session_id]["stage"],
            "original_filename": sessions[session_id]["original_filename"],
            "output_filename": sessions[session_id].get("output_filename", None)
        }
    })

@app.route('/preview/<session_id>')
def preview_video(session_id):
    logger.debug(f"Preview requested for session: {session_id}")
    
    if session_id not in sessions:
        logger.error(f"Session not found: {session_id}")
        return "Session not found", 404
    
    session_data = sessions[session_id]
    if session_data["type"] != "replace" or session_data["stage"] != "completed":
        logger.error(f"No video to preview for session: {session_id}")
        return "No video to preview", 404
    
    logger.debug(f"Rendering preview for session: {session_id}")
    return render_template('preview.html', 
                          video_url=url_for('static', filename=f'processed/{session_data["output_filename"]}'),
                          session_id=session_id,
                          company_name="Mutex")

@app.route('/cleanup/<session_id>', methods=['POST'])
def cleanup_session(session_id):
    logger.debug(f"Cleanup requested for session: {session_id}")
    
    if session_id not in sessions:
        logger.error(f"Session not found: {session_id}")
        return jsonify({"status": "error", "message": "Session not found"})
    
    try:
        session_data = sessions[session_id]
        
        # Clean up video file
        if "video_path" in session_data and os.path.exists(session_data["video_path"]):
            os.remove(session_data["video_path"])
            logger.debug(f"Removed video file: {session_data['video_path']}")
            
        # Clean up audio file
        if "audio_path" in session_data and os.path.exists(session_data["audio_path"]):
            os.remove(session_data["audio_path"])
            logger.debug(f"Removed audio file: {session_data['audio_path']}")
            
        # Clean up output file in PROCESSED_FOLDER
        if "output_path" in session_data and os.path.exists(session_data["output_path"]):
            os.remove(session_data["output_path"])
            logger.debug(f"Removed output file: {session_data['output_path']}")
            
        # Clean up output file in static folder
        if "static_output_path" in session_data and os.path.exists(session_data["static_output_path"]):
            os.remove(session_data["static_output_path"])
            logger.debug(f"Removed static output file: {session_data['static_output_path']}")
            
        # Remove session
        del sessions[session_id]
        logger.debug(f"Removed session: {session_id}")
        
        return jsonify({"status": "success", "message": "Session cleaned up successfully"})
    except Exception as e:
        logger.exception(f"Error during cleanup: {str(e)}")
        return jsonify({"status": "error", "message": f"Error during cleanup: {str(e)}"})

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    logger.error(f"404 error: {str(e)}")
    return render_template('404.html', company_name="Mutex"), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {str(e)}")
    return render_template('500.html', company_name="Mutex"), 500

if __name__ == '__main__':
    app.run(debug=True)