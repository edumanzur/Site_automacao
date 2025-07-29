"use client"

import React, { useState, useCallback } from "react"
import { Upload, FileText, Download, CheckCircle, AlertCircle, X } from "lucide-react"

interface FileState {
  file: File | null
  uploading: boolean
  processing: boolean
  progress: number
  success: boolean
  error: string | null
  downloadUrl: string | null
}

export default function PDFConverter() {
  const [fileState, setFileState] = useState<FileState>({
    file: null,
    uploading: false,
    processing: false,
    progress: 0,
    success: false,
    error: null,
    downloadUrl: null,
  })

  const resetState = () => {
    if (fileState.downloadUrl) {
      URL.revokeObjectURL(fileState.downloadUrl)
    }
    setFileState({
      file: null,
      uploading: false,
      processing: false,
      progress: 0,
      success: false,
      error: null,
      downloadUrl: null,
    })
  }

  const validateFile = (file: File): string | null => {
    if (file.type !== "application/pdf") {
      return "Please select a PDF file only."
    }
    if (file.size > 10 * 1024 * 1024) {
      return "File size must be less than 10MB."
    }
    return null
  }

  const handleFileSelect = useCallback((file: File) => {
    const error = validateFile(file)
    if (error) {
      setFileState((prev) => ({ ...prev, error, file: null }))
      return
    }

    setFileState((prev) => ({
      ...prev,
      file,
      error: null,
      success: false,
      downloadUrl: null,
    }))
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      const files = Array.from(e.dataTransfer.files)
      if (files.length > 0) {
        handleFileSelect(files[0])
      }
    },
    [handleFileSelect],
  )

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  const handleConvert = async () => {
    if (!fileState.file) return

    console.log("🚀 Iniciando conversão...")
    setFileState((prev) => ({ 
      ...prev, 
      uploading: true, 
      progress: 0, 
      error: null,
      success: false 
    }))

    try {
      // Simular progresso de upload
      for (let i = 0; i <= 30; i += 10) {
        await new Promise((resolve) => setTimeout(resolve, 100))
        setFileState((prev) => ({ ...prev, progress: i }))
      }

      // Preparar FormData
      const formData = new FormData()
      formData.append("file", fileState.file)

      console.log("📤 Enviando arquivo para o servidor...")
      setFileState((prev) => ({ ...prev, uploading: false, processing: true, progress: 40 }))

      // Fazer requisição real para o backend
      const response = await fetch("https://site-automacao.onrender.com/upload-pdf", {
        method: "POST",
        body: formData,
      })

      console.log(`📥 Resposta recebida: ${response.status} ${response.statusText}`)

      // Simular progresso de processamento
      for (let i = 50; i <= 80; i += 10) {
        await new Promise((resolve) => setTimeout(resolve, 200))
        setFileState((prev) => ({ ...prev, progress: i }))
      }

      if (!response.ok) {
        let errorMessage = "Erro no servidor"
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorMessage
        } catch {
          errorMessage = `Erro ${response.status}: ${response.statusText}`
        }
        throw new Error(errorMessage)
      }

      // Verificar content-type
      const contentType = response.headers.get('content-type')
      console.log("📄 Content-Type:", contentType)

      const blob = await response.blob()
      console.log(`📦 Blob recebido: ${blob.size} bytes`)

      if (blob.size === 0) {
        throw new Error("Arquivo retornado está vazio")
      }

      // Criar URL do blob
      const url = URL.createObjectURL(blob)
      console.log("✅ URL criada:", url)

      setFileState((prev) => ({
        ...prev,
        processing: false,
        success: true,
        progress: 100,
        downloadUrl: url,
      }))

    } catch (err) {
      console.error("❌ Erro na conversão:", err)
      const errorMessage = err instanceof Error ? err.message : "Erro desconhecido"
      setFileState((prev) => ({
        ...prev,
        uploading: false,
        processing: false,
        error: `Falha na conversão: ${errorMessage}`,
        progress: 0,
      }))
    }
  }

  const handleDownload = () => {
    if (!fileState.downloadUrl || !fileState.file) {
      console.error("❌ Tentativa de download sem URL válida")
      return
    }

    console.log("⬇️ Iniciando download...")
    
    try {
      const link = document.createElement("a")
      link.href = fileState.downloadUrl
      link.download = `${fileState.file.name.replace(".pdf", "")}_convertido.docx`
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      console.log("✅ Download iniciado com sucesso")
    } catch (error) {
      console.error("❌ Erro no download:", error)
      setFileState((prev) => ({
        ...prev,
        error: "Erro ao baixar o arquivo"
      }))
    }
  }

  const isProcessing = fileState.uploading || fileState.processing

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">PDF to DOCX Converter</h1>
          <p className="text-gray-600">Convert your PDF files to editable DOCX documents instantly</p>
          <p className="text-xs text-gray-400 mt-2">🔍 Open browser console (F12) to see debug logs</p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {/* Upload Area */}
          {!fileState.success && (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className={`
                border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200
                ${
                  fileState.file
                    ? "border-green-300 bg-green-50"
                    : "border-gray-300 hover:border-blue-400 hover:bg-blue-50"
                }
                ${isProcessing ? "pointer-events-none opacity-50" : "cursor-pointer"}
              `}
            >
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileInput}
                className="hidden"
                id="file-input"
                disabled={isProcessing}
              />

              <div className="flex flex-col items-center space-y-4">
                {fileState.file ? (
                  <>
                    <FileText className="w-16 h-16 text-green-500" />
                    <div>
                      <p className="text-lg font-semibold text-green-700">{fileState.file.name}</p>
                      <p className="text-sm text-gray-500">{(fileState.file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    <button
                      onClick={resetState}
                      className="text-red-500 hover:text-red-700 transition-colors"
                      disabled={isProcessing}
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </>
                ) : (
                  <>
                    <Upload className="w-16 h-16 text-gray-400" />
                    <div>
                      <p className="text-xl font-semibold text-gray-700 mb-2">Drop your PDF here</p>
                      <p className="text-gray-500 mb-4">or click to select a file</p>
                      <label
                        htmlFor="file-input"
                        className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors cursor-pointer"
                      >
                        Select PDF File
                      </label>
                    </div>
                    <p className="text-xs text-gray-400">Maximum file size: 10MB</p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {fileState.error && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-red-700">{fileState.error}</p>
            </div>
          )}

          {/* Progress Bar */}
          {isProcessing && (
            <div className="mt-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">
                  {fileState.uploading ? "Uploading..." : "Converting..."}
                </span>
                <span className="text-sm text-gray-500">{fileState.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${fileState.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Success State */}
          {fileState.success && (
            <div className="text-center py-8">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-2xl font-semibold text-gray-900 mb-2">Conversion Complete!</h3>
              <p className="text-gray-600 mb-6">Your PDF has been successfully converted to DOCX format.</p>
              <div className="space-y-3">
                <button
                  onClick={handleDownload}
                  className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors space-x-2"
                >
                  <Download className="w-5 h-5" />
                  <span>Download DOCX</span>
                </button>
                <div className="sm:ml-4">
                  <button
                    onClick={resetState}
                    className="w-full sm:w-auto px-6 py-3 text-gray-600 hover:text-gray-800 transition-colors"
                  >
                    Convert Another File
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Convert Button */}
          {fileState.file && !isProcessing && !fileState.success && (
            <div className="mt-6">
              <button
                onClick={handleConvert}
                className="w-full bg-blue-600 text-white py-4 px-6 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!fileState.file}
              >
                Convert to DOCX
              </button>
            </div>
          )}
        </div>

        {/* Debug Info */}
        <div className="mt-4 p-4 bg-gray-100 rounded-lg text-xs text-gray-600">
          <p><strong>Backend Status:</strong> {fileState.uploading || fileState.processing ? "Processing..." : "Ready"}</p>
          <p><strong>Server URL:</strong> https://site-automacao.onrender.com</p>
          {fileState.downloadUrl && <p><strong>Download URL:</strong> Generated ✅</p>}
        </div>
      </div>
    </div>
  )
}
