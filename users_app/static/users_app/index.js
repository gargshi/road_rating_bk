function generateMapLink(coordinates) 
{
	if (!coordinates) return '#';
	const [lat, lon] = coordinates.split(',').map(coord => coord.trim());
	return `https://www.google.com/maps?q=${lat},${lon}`;
}