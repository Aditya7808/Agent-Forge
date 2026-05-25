import { useState, useCallback } from 'react';
import { Upload, FileText, CheckCircle, ChevronLeft, ChevronRight, AlertCircle, Loader2 } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { uploadDocuments } from '../api';

export default function Sidebar({ open, setOpen, sessionId, onDocumentsUploaded, documentsUploaded }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
    },
    maxSize: 50 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadDocuments(files, sessionId);
      setUploadResult(result);
      onDocumentsUploaded();
      setFiles([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-40 bg-dark-800 border border-dark-700 rounded-r-xl p-2 hover:bg-dark-700 transition-colors"
      >
        <ChevronRight className="w-4 h-4 text-dark-400" />
      </button>
    );
  }

  return (
    <aside className="w-80 border-r border-dark-800 bg-dark-900/30 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-dark-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-dark-200">Documents</h2>
        <button onClick={() => setOpen(false)} className="p-1 hover:bg-dark-800 rounded-lg transition-colors">
          <ChevronLeft className="w-4 h-4 text-dark-500" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 ${
            isDragActive
              ? 'border-primary-500 bg-primary-500/10'
              : 'border-dark-700 hover:border-dark-500 hover:bg-dark-800/30'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className={`w-8 h-8 mx-auto mb-3 ${isDragActive ? 'text-primary-400' : 'text-dark-500'}`} />
          <p className="text-sm text-dark-300 font-medium">
            {isDragActive ? 'Drop files here' : 'Drag & drop files'}
          </p>
          <p className="text-xs text-dark-500 mt-1">PDF, DOCX, PPTX, TXT (max 50MB)</p>
        </div>

        {files.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-dark-400 uppercase tracking-wider">Queued Files</p>
            {files.map((file, i) => (
              <div key={i} className="flex items-center gap-2 bg-dark-800/50 rounded-lg px-3 py-2">
                <FileText className="w-4 h-4 text-primary-400 shrink-0" />
                <span className="text-sm text-dark-300 truncate">{file.name}</span>
                <span className="text-xs text-dark-500 ml-auto shrink-0">
                  {(file.size / 1024).toFixed(0)}KB
                </span>
              </div>
            ))}
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full btn-primary flex items-center justify-center gap-2 mt-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload & Process
                </>
              )}
            </button>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">{error}</p>
          </div>
        )}

        {uploadResult && (
          <div className="flex items-start gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <p className="text-xs text-emerald-300">{uploadResult.message}</p>
          </div>
        )}

        {documentsUploaded && (
          <div className="bg-dark-800/30 rounded-xl p-3 border border-dark-700/30">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-slow"></div>
              <span className="text-xs font-medium text-dark-300">Documents Ready</span>
            </div>
            <p className="text-xs text-dark-500 mt-1">RAG queries will search your uploaded documents</p>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-dark-800">
        <div className="glass-panel-light p-3">
          <p className="text-xs font-medium text-dark-300 mb-2">How it works</p>
          <div className="space-y-1.5">
            <p className="text-xs text-dark-500">• City/population queries → SQL Database</p>
            <p className="text-xs text-dark-500">• Document queries → RAG Pipeline</p>
            <p className="text-xs text-dark-500">• AI routes automatically</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
