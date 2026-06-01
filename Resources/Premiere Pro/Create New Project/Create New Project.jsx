var folderPath = "/Users/mjvrmqz/Personal/MVS Studios Assets/Niches/YouTube Documentary/Projects/Project 43034";
var projectName = "Project 43034.prproj";

// Create folder if it doesn't exist
var folder = new Folder(folderPath);
if (!folder.exists) folder.create();

// Create new Premiere project
app.newProject();

// Save the project
var saveFile = new File(folder.fsName + "/" + projectName);
app.project.save(saveFile);