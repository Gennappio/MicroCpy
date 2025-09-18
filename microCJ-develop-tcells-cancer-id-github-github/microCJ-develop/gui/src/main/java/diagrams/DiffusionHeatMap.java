package diagrams;

import diffusion.Diffusible;
import diffusion.DiffusionModel;
import javafx.scene.Group;
import javafx.scene.Parent;
import javafx.scene.control.Tooltip;
import javafx.scene.paint.Color;
import javafx.scene.shape.Polygon;
import javafx.scene.shape.Rectangle;

import java.util.ArrayList;
import java.util.List;

public class DiffusionHeatMap {
	private List<List<Double>> heatMapMatrix_flatX;
	private List<List<Double>> heatMapMatrix_flatY;
	private List<List<Double>> heatMapMatrix_flatZ;
	private double squareSize;
	private Diffusible substance;
	private Double minX;
	private Double maxX;

	private Double minY;
	private Double maxY;

	private Double minZ;
	private Double maxZ;

	private final static Color xColor = Color.web("#79c99e", .5);
	private final static Color yColor = Color.web("#2374ab", .5);
	private final static Color zColor = Color.web("#fb3640", .5);

	public static final boolean testing = false;
	public static final String stTesting = "HeatMap: ";

	public DiffusionHeatMap(double squareSize, Diffusible substance, DiffusionModel model){
		this.squareSize = squareSize;
		this.substance = substance;
		buildMatrix(model);
	}

	/**
	 * Builds 3 2DMatrices, each with one axis flattened.
	 * @param model the DiffusionModel from which to get the concentration data
	 */
	private void buildMatrix(DiffusionModel model) {
		heatMapMatrix_flatX = new ArrayList<>();
		heatMapMatrix_flatY = new ArrayList<>();
		heatMapMatrix_flatZ = new ArrayList<>();
		for (int n = 0; n < model.getSize(); n++) {
			List<Double> rowX = new ArrayList<>();
			List<Double> rowY = new ArrayList<>();
			List<Double> rowZ = new ArrayList<>();
			for (int m = 0; m < model.getSize(); m++) {
				Double averageX = 0.;
				Double averageY = 0.;
				Double averageZ = 0.;
				for (int p = 0; p < model.getSize(); p++) {
					averageX += model.getSubstancesAt(p, m, n).get(substance); //x
					averageY += model.getSubstancesAt(m, p, n).get(substance); //y
					averageZ += model.getSubstancesAt(m, n, p).get(substance); //z
				}
				averageX /= model.getSize();
				averageY /= model.getSize();
				averageZ /= model.getSize();
				if(minX == null || minX > averageX) minX = averageX; //finding minimum value
				if(maxX == null || maxX < averageX) maxX = averageX; //finding maximum value
				rowX.add(averageX);

				if(minY == null || minY > averageY) minY = averageY; //finding minimum value
				if(maxY == null || maxY < averageY) maxY = averageY; //finding maximum value
				rowY.add(averageY);

				if(minZ == null || minZ > averageZ) minZ = averageZ; //finding minimum value
				if(maxZ == null || maxZ < averageZ) maxZ = averageZ; //finding maximum value
				rowZ.add(averageZ);
			}
			heatMapMatrix_flatX.add(rowX);
			heatMapMatrix_flatY.add(rowY);
			heatMapMatrix_flatZ.add(rowZ);
			if(testing) System.out.println(stTesting + minX);
		}
	}

	private Parent buildSingleHeatMap(Color baseColor, List<List<Double>> matrix, double min, double max, double xOffset, double yOffset) {
		Group hm = new Group();
		for (int x = 0; x < matrix.size(); x++) {
			List<Double> row = matrix.get(x);
			for (int y = 0; y < row.size(); y++) {
				double value = row.get(y);
				double opacity = (value - min)/(max - min);
				Rectangle square = new Rectangle(squareSize * x + xOffset, squareSize * y + yOffset, squareSize, squareSize);
				square.setStroke(Color.BLACK);
				square.setFill(baseColor.deriveColor(1.,1.,1., opacity));
				hm.getChildren().add(square);
			}
		}
		if(testing) {
			Tooltip tooltip = new Tooltip("Min:" + String.format("%.3f", min) + " /Max:" + String.format("%.3f", max));
			Tooltip.install(hm, tooltip);
		}
		return hm;
	}

	public Parent buildHeatMap(Color baseColor) {
		Group hm = new Group();
		double offset = squareSize * (heatMapMatrix_flatY.size() + 3);
		double background_size = offset - squareSize * 2;
		double h = squareSize * heatMapMatrix_flatX.size();
		double gap = squareSize/2;

		Rectangle backgroundZ = new Rectangle(0, 0, background_size, background_size);
		backgroundZ.setFill(zColor);
		Rectangle backgroundY = new Rectangle(0, offset, background_size, background_size);
		backgroundY.setFill(yColor);
		Rectangle backgroundX = new Rectangle(offset, 0, background_size, background_size);
		backgroundX.setFill(xColor);
		hm.getChildren().addAll(backgroundX, backgroundY, backgroundZ);

		Rectangle whiteFillZ = new Rectangle(gap, gap, h, h);
		Rectangle whiteFillY = new Rectangle(gap, offset + gap, h, h);
		Rectangle whiteFillX = new Rectangle(offset + gap, gap, h, h);
		whiteFillX.setFill(Color.WHITE);
		whiteFillY.setFill(Color.WHITE);
		whiteFillZ.setFill(Color.WHITE);
		hm.getChildren().addAll(whiteFillX, whiteFillY, whiteFillZ);

		hm.getChildren().add(buildSingleHeatMap(baseColor, heatMapMatrix_flatZ, minZ, maxZ, gap, gap));
		hm.getChildren().add(buildSingleHeatMap(baseColor, heatMapMatrix_flatY, minY, maxY, gap, offset + gap));
		hm.getChildren().add(buildSingleHeatMap(baseColor, heatMapMatrix_flatX, minX, maxX, offset + gap, gap));

		//cube
		hm.getChildren().add(drawCube(h/2, 1.7 * h + squareSize, 1.7 * h + squareSize, squareSize));
		return hm;
	}

	private Parent drawCube(double a, double ox, double oy, double d) {
		double c = Math.sqrt(Math.pow(a, 2) / 3);
		double p1x = ox - c;    double p1y = oy - a / 2;
		double p2x = ox;        double p2y = oy - a;
		double p3x = ox + c;    double p3y = p1y;
		Polygon up = new Polygon(ox, oy, p1x, p1y, p2x, p2y, p3x, p3y);
		up.setFill(zColor);

		double p7x = ox + d / 2;    double p7y = oy + Math.sqrt(Math.pow(d, 2) / 3);
		double p4x = p7x + c;       double p4y = p7y - a / 2;
		double p5x = p4x;           double p5y = p4y + a;
		double p6x = p7x;           double p6y = p7y + a;
		Polygon right = new Polygon(p7x, p7y, p4x, p4y, p5x, p5y, p6x, p6y);
		right.setFill(xColor);

		double p8x = p7x - d;       double p8y = p7y;
		double p9x = p8x;           double p9y = p8y + a;
		double p10x = p9x - c;      double p10y = p5y;
		double p11x = p10x;         double p11y = p10y - a;
		Polygon left = new Polygon(p8x, p8y, p9x, p9y, p10x, p10y, p11x, p11y);
		left.setFill(yColor);

		return new Group(up, right, left);
	}
}
