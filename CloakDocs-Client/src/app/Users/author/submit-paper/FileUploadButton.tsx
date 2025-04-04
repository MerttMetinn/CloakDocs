'use client';

import React, { useState, useEffect } from 'react';

interface FileUploadButtonProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  disabled?: boolean;
  id?: string;
}

export default function FileUploadButton({ 
  onFileSelect, 
  selectedFile,
  disabled = false, 
  id = "file-upload" 
}: FileUploadButtonProps) {
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  // selectedFile değiştiğinde fileName'i güncelle
  useEffect(() => {
    if (selectedFile) {
      setFileName(selectedFile.name);
    } else {
      setFileName(null);
    }
  }, [selectedFile]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setFileError(null);
    
    if (file) {
      // Dosya boyutu kontrolü (16MB)
      if (file.size > 16 * 1024 * 1024) {
        setFileError('Dosya boyutu 16MB\'dan büyük olamaz.');
        return;
      }
      
      // Dosya tipi kontrolü
      if (file.type !== 'application/pdf') {
        setFileError('Sadece PDF dosyaları kabul edilmektedir.');
        return;
      }
      
      setFileName(file.name);
      onFileSelect(file);
    }
  };

  const handleButtonClick = () => {
    document.getElementById(id)?.click();
  };

  return (
    <div className="border-2 border-dashed border-border rounded-md p-8 text-center">
      <div className="mb-4">
        <svg className="mx-auto h-12 w-12 text-text-primary opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      </div>
      
      {fileError && (
        <div className="mb-4 text-status-error font-medium">
          {fileError}
        </div>
      )}
      
      {fileName ? (
        <div className="mb-2 text-text-primary">
          <span className="font-semibold">{fileName}</span> seçildi
        </div>
      ) : (
        <p className="mb-2 text-text-primary">
          <span className="font-semibold">PDF dosyanızı sürükleyip bırakın</span> veya dosya seçmek için tıklayın
        </p>
      )}
      
      <input
        id={id}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        required
        onChange={handleFileChange}
        disabled={disabled}
      />
      
      <button
        type="button"
        onClick={handleButtonClick}
        className="button-outline mt-4"
        disabled={disabled}
      >
        Dosya Seç
      </button>
    </div>
  );
} 