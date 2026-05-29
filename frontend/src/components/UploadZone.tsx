import { useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { uploadCSV } from "@/api";

export function UploadZone({ onUpload }: { onUpload: () => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".csv")) return;
      setUploading(true);
      try {
        await uploadCSV(file);
        onUpload();
      } catch (e) {
        alert("Upload failed: " + (e as Error).message);
      } finally {
        setUploading(false);
      }
    },
    [onUpload]
  );

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => setIsDragging(false);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <Card className="flex-shrink-0 w-[260px] border-dashed border-2">
      <CardContent
        className={`flex flex-col items-center justify-center h-full min-h-[200px] p-6 cursor-pointer transition-colors ${
          isDragging ? "bg-blue-50 border-blue-400" : "bg-white"
        }`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => document.getElementById("fileInput")?.click()}
      >
        <input
          id="fileInput"
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        {uploading ? (
          <span className="text-sm text-gray-500">Uploading...</span>
        ) : (
          <>
            <div className="text-2xl mb-2">📄</div>
            <h3 className="text-sm font-semibold mb-1">Upload CSV Report</h3>
            <p className="text-xs text-gray-500 text-center">
              Drop an Accela export here or click to browse
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
