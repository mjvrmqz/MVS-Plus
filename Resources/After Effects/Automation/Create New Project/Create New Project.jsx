var folderPath = "/Users/mjvrmqz/Personal/MVS Studios Assets/Niches/YouTube Documentary/Projects/Project 43034";
var projectName = "Project 43034.aep";

var folder = new Folder(folderPath);
if (!folder.exists) folder.create();

app.newProject();

var saveFile = new File(folder.fsName + "/" + projectName);
app.project.save(saveFile);