package geom.twoDim;

import core.SettingsProvider;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;

import java.io.FileReader;
import java.io.IOException;
import java.io.Reader;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ImporterDistributor extends Distributor2D {
	private final Map<String, Point2D> identityLocationMap = new HashMap<>();
	private final EmptiableMatrix<String> matrix;
	private final String emptyValue;

	public ImporterDistributor(double gap) {
		super(gap, false); //never cache this
		this.emptyValue = "";

		Iterable<CSVRecord> records = null;
		try {
			String id = SettingsProvider.SETTINGS_PROVIDER.getString("gene-status-data.id");
			Reader in = new FileReader("sc/" + id +"_coordinates.csv");
			records = CSVFormat.DEFAULT.withFirstRecordAsHeader().parse(in);

			int maxRowIndex = 0;
			int maxColIndex = 0;
			Map<String, Integer[]> data = new HashMap<>();
			for (CSVRecord record : records) { //determine the highest row and column indexes, and store data in a list
				String ident = record.get("spot");
				int row = (int) Double.parseDouble(record.get("y"));
				int col = (int) Double.parseDouble(record.get("x"));
				data.put(ident, new Integer[]{row, col});
				if (row > maxRowIndex) maxRowIndex = row;
				if (col > maxColIndex) maxColIndex = col;
			}
			EmptiableMatrix<String> matrix = new EmptiableMatrix<>(maxRowIndex, maxColIndex, emptyValue);

			for (String ident : data.keySet()) {
				var indexes = data.get(ident);
				matrix.put(indexes[0], indexes[1], ident);
			}
			this.matrix = matrix;

		} catch (IOException e) {
			throw new IllegalStateException("Coordinates files couldn't be imported");
		}
	}

	@Override
	public void populate(int n) {
		setTotal(n);
		repopulate();
	}

	public void repopulate() {
		int cu = 0;
		for (int i = 0; i <= matrix.getMaxRowIndex(); i++) {
			for (int j = 0; j <= matrix.getMaxColIndex(); j++) {
				String atPos = matrix.get(i, j);
				if (!atPos.equals(emptyValue)) {
					Point2D location = new Point2D(j * getGap() / 2, i * getGap() / 1.1);
					identityLocationMap.put(atPos, location);
					cu++;
					if (cu == getTotal()) return;
				}
			}
		}
	}

	@Override
	public void shove() {
		//todo implement?
	}

	@Override
	public Point2D locateEmptySpotNextTo(Point2D location) {
		return null; //todo implement
	}

	@Override
	public Point2D getArbitraryPointNextTo(Point2D origin) {
		return null;
	}

	@Override
	public List<Point2D> getLocations() {
		return List.copyOf(identityLocationMap.values());
	}

	public Map<String, Point2D> getMap() {
		return identityLocationMap;
	}
}
