// function generateMapLink(coordinates) 
// {
// 	if (!coordinates) return '#';
// 	const [lat, lon] = coordinates.split(',').map(coord => coord.trim());
// 	return `https://www.google.com/maps?q=${lat},${lon}`;
// }
function generateMapLink(coordinates) {
    if (!coordinates || typeof coordinates !== "string") {
        return "#"; // fallback if coordinates are missing
    }

    const parts = coordinates.split(',').map(coord => coord.trim());

    if (parts.length !== 2) {
        return "#"; // invalid format
    }

    const [lat, lon] = parts;
    return `https://www.google.com/maps?q=${lat},${lon}`;
}
