var folderPath = "/Users/mjvrmqz/Personal/MVS Studios Assets/Niches/YouTube Documentary/Projects/Project 43034";
var projectName = "Project 43034.psd";

// Create folder if it doesn't exist
var folder = new Folder(folderPath);
if (!folder.exists) folder.create();

// Create new document
var docWidth = 1920;
var docHeight = 1080;
var docResolution = 72;
var docName = projectName.replace(".psd","");

var newDoc = app.documents.add(docWidth, docHeight, docResolution, docName, NewDocumentMode.RGB, DocumentFill.WHITE);

// Save the PSD
var saveFile = new File(folder.fsName + "/" + projectName);
var psdSaveOptions = new PhotoshopSaveOptions();
newDoc.saveAs(saveFile, psdSaveOptions, true, Extension.LOWERCASE);