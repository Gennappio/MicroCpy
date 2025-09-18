package gui;

import core.SettingsProvider;
import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.fxml.FXML;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.TextField;
import javafx.scene.paint.Color;
import javafx.scene.text.Text;
import javafx.stage.Stage;

import java.io.IOException;

public class StartController {
		@FXML private Button b3d;
		@FXML private Button b2d;
		@FXML private Button bSettings;
		@FXML private Text tAbout;
		@FXML private TextField tfSettings;

		@FXML public void initialize(){
			tAbout.setText("MicroCJ created by Pedro Victori (Buffa lab) \n" +
					"Released under the Apache License 2.0. \n" +
					"https://github.com/CBigOxf/microCJ \n" +
					"https://www.oncology.ox.ac.uk/team/francesca-buffa");
		}

	@FXML protected void handleButtonAction(ActionEvent event) throws IOException {
		Button pressedButton = (Button) event.getSource();
		Stage stage = (Stage) pressedButton.getScene().getWindow();
		SettingsProvider.setUserSettings(tfSettings.getText() + ".xml");
		if (pressedButton == b3d) loadController(stage, new MainController3D());
		else if(pressedButton == b2d) loadController(stage, new MainController2D());
		//else if(pressedButton == bSettings) //todo implement
	}

	private void loadController(Stage stage, MainController controller) {
		FXMLLoader fxmlLoader = new FXMLLoader(getClass().getResource("/fxml/main.fxml"));
		fxmlLoader.setController(controller);
		Parent root;
		try {
			root = fxmlLoader.load();
			Scene scene = new Scene(root, 1600, 1000, true);
			scene.getStylesheets().add(getClass().getResource("/css/bootstrap3.css").toExternalForm());
			scene.setFill(Color.WHITE);
			stage.setScene(scene);
			stage.setMaximized(true);
			stage.show();
			controller.setScene(scene);
		} catch (IOException e) {
			e.printStackTrace();
		}
	}


}
